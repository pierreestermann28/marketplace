from django.conf import settings
from django.db import models

from .listing import Listing


class ListingChangeLog(models.Model):
    class ActorRole(models.TextChoices):
        SELLER = "seller", "Vendeur"
        ADMIN = "admin", "Admin"
        SYSTEM = "system", "Système"

    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="change_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    actor_role = models.CharField(
        max_length=16, choices=ActorRole.choices, default=ActorRole.SELLER
    )
    event = models.CharField(max_length=24, choices=Listing.ChangeEvent.choices)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_event_display()} ({self.listing_id})"
