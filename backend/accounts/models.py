from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from accounts.managers import UserManager


class User(AbstractUser):
    """A GrocerEase shopper account identified by a unique email address."""

    username = None
    first_name = None
    last_name = None
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['display_name']

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email=Lower('email')),
                name='accounts_user_email_lowercase',
            ),
        ]

    def _normalize_email(self):
        if self.email:
            self.email = self.email.strip().lower()

    def clean(self):
        super().clean()
        self._normalize_email()

    def save(self, *args, **kwargs):
        self._normalize_email()
        return super().save(*args, **kwargs)

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name


class PasswordResetEmailJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        PROCESSING = 'PROCESSING', 'Processing'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_email_jobs',
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user',),
                condition=Q(status__in=('QUEUED', 'PROCESSING')),
                name='accounts_one_active_reset_email_per_user',
            ),
        ]
        indexes = [
            models.Index(
                fields=('status', 'available_at', 'created_at'),
                name='accounts_reset_job_queue_idx',
            ),
        ]
