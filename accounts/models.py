# accounts/models.py
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class EmailUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
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


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses"
    )

    label = models.CharField(max_length=60, default="Home")
    full_name = models.CharField(max_length=120)
    line1 = models.CharField(max_length=120)
    line2 = models.CharField(max_length=120, blank=True)

    postal_code = models.CharField(max_length=20, db_index=True)
    city = models.CharField(max_length=80, db_index=True)
    country_code = models.CharField(max_length=2, default="FR")
    phone_e164 = models.CharField(max_length=32, blank=True)

    is_default = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ReputationStats(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reputation"
    )

    # Reviews
    seller_rating_avg = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal("0.00")
    )
    seller_rating_count = models.PositiveIntegerField(default=0)

    buyer_rating_avg = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal("0.00")
    )
    buyer_rating_count = models.PositiveIntegerField(default=0)

    # Transactions (real completed orders)
    items_sold_count = models.PositiveIntegerField(default=0)
    items_bought_count = models.PositiveIntegerField(default=0)

    # Optional penalties (V1 keep, you can wire later)
    cancellations_count = models.PositiveIntegerField(default=0)
    no_show_count = models.PositiveIntegerField(default=0)
    disputes_count = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def for_user(cls, user):
        stats, _ = cls.objects.get_or_create(user=user)
        return stats


@receiver(post_save, sender=User)
def ensure_reputation_stats(sender, instance, created, **kwargs):
    if created:
        ReputationStats.objects.get_or_create(user=instance)
