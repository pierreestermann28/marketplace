from django.conf import settings
from django.db import models
from django.db.models import F
from django.utils import timezone


def current_month_period():
    now = timezone.now()
    return now.date().replace(day=1)


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
        return f"Entitlement for {self.user.email}"

    @property
    def is_premium_active(self):
        if not self.is_premium:
            return False
        if self.premium_until and self.premium_until < timezone.now():
            return False
        return True


class UsageCounter(models.Model):
    SCOPE_LISTING_PUBLICATION = "listing_publication"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_counters",
    )
    scope = models.CharField(max_length=64, db_index=True)
    period = models.DateField(default=current_month_period, db_index=True)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "scope", "period")

    def increment(self, amount=1):
        type(self).objects.filter(pk=self.pk).update(count=F("count") + amount)
        self.refresh_from_db(fields=["count"])
