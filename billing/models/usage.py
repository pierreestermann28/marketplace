from django.conf import settings
from django.db import models

from billing.models.utils import current_month_period


class UsageCounter(models.Model):
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

    def increment(self, amount: int = 1):
        self.count += amount
        self.save(update_fields=["count"])

    def __str__(self):
        return (
            f"UsageCounter(user_id={self.user_id}, scope={self.scope}, "
            f"period={self.period}, count={self.count})"
        )
