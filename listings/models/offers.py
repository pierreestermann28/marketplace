import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class OfferQuerySet(models.QuerySet):
    def active(self):
        now = timezone.now()
        return self.filter(
            status="requested",
            cancelled_at__isnull=True,
            expires_at__gt=now,
        )

    def expired(self):
        now = timezone.now()
        return self.filter(
            status="requested",
            cancelled_at__isnull=True,
            expires_at__lte=now,
        )


class Offer(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Offre envoyée"
        ACCEPTED = "accepted", "Offre acceptée"
        REJECTED = "rejected", "Offre refusée"
        CANCELLED = "cancelled", "Offre annulée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="offers"
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offers"
    )

    offer_price_cents = models.PositiveIntegerField(db_index=True)
    currency = models.CharField(max_length=3, default="EUR")

    note = models.TextField(blank=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.REQUESTED, db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)

    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="offers_decided",
    )

    objects = OfferQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["listing", "status", "expires_at"]),
            models.Index(fields=["buyer", "status", "expires_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "buyer"], name="uniq_offer_per_buyer_listing"
            ),
            models.UniqueConstraint(
                fields=["listing"],
                condition=Q(status="accepted", cancelled_at__isnull=True),
                name="uniq_accepted_offer_per_listing",
            ),
        ]

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def is_active(self) -> bool:
        return (
            self.status == self.Status.REQUESTED
            and self.cancelled_at is None
            and not self.is_expired()
        )


class OfferLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Offre créée"
        CANCELLED = "cancelled", "Offre annulée"
        ACCEPTED = "accepted", "Offre acceptée"
        REJECTED = "rejected", "Offre refusée"

    offer = models.ForeignKey(
        "listings.Offer", on_delete=models.CASCADE, related_name="logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offer_logs"
    )

    action = models.CharField(max_length=16, choices=Action.choices, db_index=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["offer", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} ({self.offer_id})"
