from django.conf import settings
from django.db import models


class OnboardingProfile(models.Model):
    PURPOSE_CHOICES = [
        ("buy", "Acheter"),
        ("sell", "Vendre"),
        ("both", "Acheter & Vendre"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="onboarding_profile",
    )
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES, default="buy")

    location_city = models.ForeignKey(
        "location.City",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="onboarding_profiles",
    )
    radius_km = models.PositiveIntegerField(null=True, blank=True)
    categories = models.ManyToManyField(
        "catalog.Category",
        blank=True,
        related_name="onboarding_profiles",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OnboardingProfile({getattr(self.user, 'email', self.user_id)})"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"], name="uniq_favorite_user_listing"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["listing", "created_at"]),
        ]
