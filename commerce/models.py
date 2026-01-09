import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from accounts.models import Address
from listings.models import Listing


class Order(models.Model):
    class Fulfillment(models.TextChoices):
        SHIPPING = "shipping"
        IN_PERSON = "in_person"

    class Status(models.TextChoices):
        CREATED = "created"
        PAID = "paid"
        MEETUP_SCHEDULED = "meetup_scheduled"
        LABEL_READY = "label_ready"
        IN_TRANSIT = "in_transit"
        AWAITING_CONFIRMATION = "awaiting_confirmation"
        COMPLETED = "completed"
        CANCELLED = "cancelled"
        REFUNDED = "refunded"
        DISPUTE = "dispute"
        EXPIRED = "expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    listing = models.ForeignKey(
        Listing, on_delete=models.PROTECT, related_name="orders"
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

    item_price_cents = models.PositiveIntegerField()
    shipping_price_cents = models.PositiveIntegerField(default=0)
    platform_fee_cents = models.PositiveIntegerField(default=0)
    stripe_fee_cents = models.PositiveIntegerField(default=0)
    total_paid_cents = models.PositiveIntegerField(default=0)
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

    # in-person proof
    handover_code = models.CharField(max_length=12, blank=True, db_index=True)
    handover_confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmation_deadline = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Payment(models.Model):
    class Provider(models.TextChoices):
        STRIPE = "stripe"

    class Status(models.TextChoices):
        REQUIRES_ACTION = "requires_action"
        SUCCEEDED = "succeeded"
        FAILED = "failed"
        REFUNDED = "refunded"

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment"
    )
    provider = models.CharField(
        max_length=12, choices=Provider.choices, default=Provider.STRIPE
    )
    status = models.CharField(max_length=24, choices=Status.choices, db_index=True)

    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="EUR")

    provider_payment_intent_id = models.CharField(
        max_length=120, blank=True, db_index=True
    )
    provider_charge_id = models.CharField(max_length=120, blank=True, db_index=True)
    raw = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class Dispute(models.Model):
    class Reason(models.TextChoices):
        NO_SHOW = "no_show"
        NOT_AS_DESCRIBED = "not_as_described"
        NOT_RECEIVED = "not_received"
        OTHER = "other"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="disputes")
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="disputes_opened",
    )
    reason = models.CharField(max_length=30, choices=Reason.choices, db_index=True)
    message = models.TextField(blank=True)

    is_resolved = models.BooleanField(default=False, db_index=True)
    resolution = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


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
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("order", "role")]
        indexes = [models.Index(fields=["target", "role", "created_at"])]
