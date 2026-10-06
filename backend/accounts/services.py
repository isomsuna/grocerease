import logging
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from accounts.models import PasswordResetEmailJob, User

logger = logging.getLogger(__name__)
RESET_EMAIL_MAX_ATTEMPTS = 5
RESET_EMAIL_LEASE = timedelta(minutes=5)


class EmailAlreadyRegistered(Exception):
    """Raised when a registration loses a concurrent email uniqueness race."""


def register_user(*, email: str, display_name: str, password: str) -> User:
    try:
        with transaction.atomic():
            return User.objects.create_user(
                email=email,
                display_name=display_name,
                password=password,
            )
    except IntegrityError as exc:
        raise EmailAlreadyRegistered from exc


def authenticate_user(*, email: str, password: str) -> User | None:
    return authenticate(email=email.strip(), password=password)


def password_validation_errors(password: str, user: User) -> list[str]:
    try:
        validate_password(password, user)
    except ValidationError as exc:
        return list(exc.messages)
    return []


def send_password_reset(*, email: str) -> None:
    user = User.objects.filter(email__iexact=email.strip()).first()
    if user is None or not user.is_active:
        return

    PasswordResetEmailJob.objects.get_or_create(user=user)


def _password_reset_link(user: User) -> tuple[str, str, str]:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    parts = urlsplit(settings.FRONTEND_PASSWORD_RESET_URL)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in {'uid', 'token'}
    ]
    query.extend((('uid', uid), ('token', token)))
    link = urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode(query),
        parts.fragment,
    ))
    return link, uid, token


def _claim_password_reset_email_job(*, now=None) -> int | None:
    now = now or timezone.now()
    expired_lease = now - RESET_EMAIL_LEASE
    with transaction.atomic():
        job = (
            PasswordResetEmailJob.objects.select_for_update(skip_locked=True)
            .filter(
                Q(status=PasswordResetEmailJob.Status.QUEUED, available_at__lte=now)
                | Q(
                    status=PasswordResetEmailJob.Status.PROCESSING,
                    locked_at__lte=expired_lease,
                )
            )
            .order_by('created_at', 'pk')
            .first()
        )
        if job is None:
            return None
        job.status = PasswordResetEmailJob.Status.PROCESSING
        job.locked_at = now
        job.attempt_count += 1
        job.save(update_fields=('status', 'locked_at', 'attempt_count'))
        return job.pk


def _retry_or_discard_password_reset_email(job: PasswordResetEmailJob) -> None:
    if job.attempt_count >= RESET_EMAIL_MAX_ATTEMPTS:
        job.delete()
        logger.error('Password reset email delivery failed after maximum retries.')
        return

    retry_delay = min(30 * (2 ** (job.attempt_count - 1)), 3600)
    job.status = PasswordResetEmailJob.Status.QUEUED
    job.available_at = timezone.now() + timedelta(seconds=retry_delay)
    job.locked_at = None
    job.save(update_fields=('status', 'available_at', 'locked_at'))


def _deliver_password_reset_email_job(job_id: int) -> None:
    try:
        job = PasswordResetEmailJob.objects.select_related('user').get(pk=job_id)
    except PasswordResetEmailJob.DoesNotExist:
        return

    if not job.user.is_active:
        job.delete()
        return

    link, uid, token = _password_reset_link(job.user)
    try:
        delivered = send_mail(
            subject='Reset your GrocerEase password',
            message=f'Use this link to choose a new password: {link}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[job.user.email],
            fail_silently=False,
        )
        if delivered < 1:
            raise OSError('Email backend did not send the reset message.')
    except Exception as exc:
        _log_password_reset_email_failure(exc, link, uid, token)
        job.refresh_from_db()
        _retry_or_discard_password_reset_email(job)
    else:
        job.delete()


def process_password_reset_email_jobs(*, batch_size: int = 10) -> int:
    processed = 0
    for _ in range(max(0, batch_size)):
        job_id = _claim_password_reset_email_job()
        if job_id is None:
            break
        _deliver_password_reset_email_job(job_id)
        processed += 1
    return processed


def _log_password_reset_email_failure(exc: Exception, *secrets: str) -> None:
    safe_message = str(exc)
    for secret in secrets:
        if secret:
            safe_message = safe_message.replace(secret, '[redacted]')
    logger.error(
        'Password reset email delivery failed (%s): %s',
        type(exc).__name__,
        safe_message,
    )


def reset_password(*, uid: str, token: str, new_password: str) -> tuple[User | None, list[str]]:
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None, []

    if not default_token_generator.check_token(user, token):
        return None, []

    errors = password_validation_errors(new_password, user)
    if errors:
        return user, errors

    user.set_password(new_password)
    user.save(update_fields=('password',))
    return user, []


def change_password(*, user: User, current_password: str, new_password: str) -> tuple[bool, list[str]]:
    if not user.check_password(current_password):
        return False, []
    errors = password_validation_errors(new_password, user)
    if errors:
        return True, errors

    user.set_password(new_password)
    user.save(update_fields=('password',))
    return True, []
