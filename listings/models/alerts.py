from django.conf import settings
from django.db import models


class ListingReminder(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_reminders",
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="reminders"
    )

    notify_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"], name="uniq_listing_reminder_user_listing"
            ),
        ]


class SearchAlert(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_alerts",
    )
    keyword = models.CharField(max_length=255, blank=True)
    location_city = models.ForeignKey(
        "location.City",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="search_alerts",
    )
    category = models.ForeignKey(
        "catalog.Category",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="search_alerts",
    )

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "keyword", "location_city", "category"],
                name="uniq_search_alert",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active", "created_at"]),
        ]

    def __str__(self):
        parts = [self.keyword or "mot-clé libre"]
        if self.location_city:
            parts.append(self.location_city.name)
        if self.category:
            parts.append(self.category.name)
        return " · ".join(parts)


class SearchAlertNotification(models.Model):
    alert = models.ForeignKey(
        "listings.SearchAlert", on_delete=models.CASCADE, related_name="notifications"
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="alert_notifications"
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["alert", "listing"], name="uniq_search_alert_notification"
            ),
        ]
