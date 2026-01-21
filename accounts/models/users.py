from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class EmailUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields) -> "User":
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)

    display_name = models.CharField(max_length=80, blank=True)
    phone_e164 = models.CharField(max_length=32, blank=True, db_index=True)

    is_verified = models.BooleanField(default=False, db_index=True)

    trust_score = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("0.00"), db_index=True
    )
    stripe_customer_id = models.CharField(
        max_length=64, blank=True, null=True, db_index=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = EmailUserManager()

    def __str__(self):
        return self.email
