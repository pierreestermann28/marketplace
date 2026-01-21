import uuid

from django.conf import settings
from django.db import models


class Order(models.Model):
    class Fulfillment(models.TextChoices):
        SHIPPING = "shipping"
        IN_PERSON = "in_person"

    class Status(models.TextChoices):
        CREATED = "created"
        MEETUP_SCHEDULED = "meetup_scheduled"
        IN_TRANSIT = "in_transit"
        AWAITING_CONFIRMATION = "awaiting_confirmation"
        COMPLETED = "completed"
        CANCELLED = "cancelled"
        EXPIRED = "expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    listing = models.OneToOneField(
        "listings.Listing",
        on_delete=models.PROTECT,
        related_name="order",
    )

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchases"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales"
    )

    fulfillment = models.CharField(
        max_length=16, choices=Fulfillment.choices, db_index=True
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.CREATED, db_index=True
    )

    proposed_price_cents = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="EUR")

    buyer_address = models.ForeignKey(
        "accounts.Address",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="orders_as_destination",
    )
    seller_address = models.ForeignKey(
        "accounts.Address",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="orders_as_origin",
    )

    handover_code = models.CharField(max_length=12, blank=True, db_index=True)
    handover_confirmed_at = models.DateTimeField(null=True, blank=True)

    confirmation_deadline = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["seller", "status", "created_at"]),
            models.Index(fields=["buyer", "status", "created_at"]),
        ]
