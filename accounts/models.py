from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    display_name = models.CharField(max_length=80, blank=True)
    phone_e164 = models.CharField(max_length=32, blank=True, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    trust_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
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
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reputation",
    )

    seller_rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    seller_rating_count = models.PositiveIntegerField(default=0)
    items_sold_count = models.PositiveIntegerField(default=0)

    buyer_rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    buyer_rating_count = models.PositiveIntegerField(default=0)
    items_bought_count = models.PositiveIntegerField(default=0)

    cancellations_count = models.PositiveIntegerField(default=0)
    no_show_count = models.PositiveIntegerField(default=0)
    disputes_count = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)
