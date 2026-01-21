from django.conf import settings
from django.db import models


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
