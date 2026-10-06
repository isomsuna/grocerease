from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

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
            models.UniqueConstraint(Lower('email'), name='accounts_user_email_ci_uniq'),
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
