# billing/models.py
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


def current_month_period():
    today = timezone.localdate()
    return today.replace(day=1)


class UserEntitlement(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="entitlement",
    )

    is_premium = models.BooleanField(default=False, db_index=True)
    premium_until = models.DateTimeField(null=True, blank=True)

    free_listing_quota = models.PositiveIntegerField(default=3)
    free_detected_item_quota = models.PositiveIntegerField(default=5)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User entitlement"
        verbose_name_plural = "User entitlements"

    def __str__(self):
        return f"Entitlement(user_id={self.user_id})"

    @property
    def is_premium_active(self) -> bool:
        if not self.is_premium:
            return False
        if self.premium_until and self.premium_until < timezone.now():
            return False
        return True


class UsageCounter(models.Model):
    # Scopes (keep these constants here)
    SCOPE_LISTING_PUBLICATION = "listing_publication"
    SCOPE_DETECTED_ITEM = "detected_item"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_counters",
    )
    scope = models.CharField(max_length=64, db_index=True)
    period = models.DateField(default=current_month_period, db_index=True)
    count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "scope", "period"],
                name="uniq_usage_counter_user_scope_period",
            )
        ]
        indexes = [
            models.Index(fields=["user", "scope", "period"]),
            models.Index(fields=["period", "scope"]),
        ]

    def __str__(self):
        return (
            f"UsageCounter(user_id={self.user_id}, scope={self.scope}, "
            f"period={self.period}, count={self.count})"
        )
