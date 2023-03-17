# pylint: disable=missing-module-docstring, missing-function-docstring
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from tradecore_api.models.managers.user_manager import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    This class for creating users.
    """

    email = models.EmailField(max_length=100, unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    auth_token = models.TextField(blank=True, null=True)
    token_authenticated_at = models.DateTimeField(blank=True, null=True)
    geolocation_data = models.JSONField(default=dict, blank=True)
    joined_on_holiday = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        self.full_clean(exclude=["password"])
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def full_name(self):
        return f"{self.first_name} {self.last_name}"
