from django.contrib.auth.models import AbstractUser
from django.db import models

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

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name
