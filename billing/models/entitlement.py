from django.conf import settings
from django.db import models
from django.utils import timezone


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
