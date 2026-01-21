import uuid

from django.db import models


class AISuggestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    analysis = models.OneToOneField(
        "ai.AIImageAnalysis", on_delete=models.CASCADE, related_name="suggestion"
    )
    listing = models.ForeignKey(
        "listings.Listing",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_suggestions",
    )

    suggested_category_slug = models.CharField(max_length=64, blank=True)
    suggested_title = models.CharField(max_length=120, blank=True)
    suggested_condition = models.CharField(max_length=20, blank=True)
    suggested_attributes = models.JSONField(default=dict)
    price_eur_min = models.PositiveIntegerField(null=True, blank=True)
    price_eur_max = models.PositiveIntegerField(null=True, blank=True)

    pricing_reason = models.CharField(max_length=280, blank=True)
    quality_flags = models.JSONField(default=list, blank=True)

    user_accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
