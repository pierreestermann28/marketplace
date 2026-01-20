# commerce/models.py
import uuid
import secrets

from django.conf import settings
from django.db import models
from accounts.models import Address
from listings.models import Listing


class Order(models.Model):
    class Fulfillment(models.TextChoices):
        SHIPPING = "shipping"
        IN_PERSON = "in_person"

    class Status(models.TextChoices):
        CREATED = "created"  # reservation created
        MEETUP_SCHEDULED = "meetup_scheduled"
        IN_TRANSIT = "in_transit"  # if shipping (no payment)
        AWAITING_CONFIRMATION = "awaiting_confirmation"
        COMPLETED = "completed"
        CANCELLED = "cancelled"
        EXPIRED = "expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    listing = models.OneToOneField(
        Listing,
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

    # Optional info (because no in-app payment)
    proposed_price_cents = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="EUR")

    buyer_address = models.ForeignKey(
        Address,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="orders_as_destination",
    )
    seller_address = models.ForeignKey(
        Address,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="orders_as_origin",
    )

    # in-person proof / or pickup confirmation
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


class Review(models.Model):
    class Role(models.TextChoices):
        BUYER_TO_SELLER = "buyer_to_seller"
        SELLER_TO_BUYER = "seller_to_buyer"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_written",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_received",
    )

    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "role"], name="uniq_review_per_role_order"
            )
        ]
        indexes = [
            models.Index(fields=["target", "role", "created_at"]),
        ]
