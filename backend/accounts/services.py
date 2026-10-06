import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from accounts.models import User

logger = logging.getLogger(__name__)
password_reset_email_executor = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix='password-reset-email',
)


class EmailAlreadyRegistered(Exception):
    """Raised when a registration loses a concurrent email uniqueness race."""


def register_user(*, email: str, display_name: str, password: str) -> User:
    user = User(email=email, display_name=display_name)
    try:
        with transaction.atomic():
            return User.objects.create_user(
                email=user.email,
                display_name=user.display_name,
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

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = settings.FRONTEND_PASSWORD_RESET_URL
    link = f'{reset_url}?{urlencode({"uid": uid, "token": token})}'

    try:
        password_reset_email_executor.submit(
            _deliver_password_reset_email,
            user.email,
            link,
            uid,
            token,
        )
    except Exception as exc:
        _log_password_reset_email_failure(exc, link, uid, token)


def _deliver_password_reset_email(recipient: str, link: str, uid: str, token: str) -> None:
    try:
        delivered = send_mail(
            subject='Reset your GrocerEase password',
            message=f'Use this link to choose a new password: {link}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as exc:
        _log_password_reset_email_failure(exc, link, uid, token)
    else:
        if not delivered:
            logger.warning('Password reset email delivery failed.')


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
