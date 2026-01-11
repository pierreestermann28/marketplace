# ingestion/models.py
from django.conf import settings
from django.db import models


class DetectedItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Proposition en attente"
        USER_APPROVED = "USER_APPROVED", "Validée par le vendeur"
        USER_REJECTED = "USER_REJECTED", "Rejetée par le vendeur"
        ADMIN_APPROVED = "ADMIN_APPROVED", "Validée par l’équipe"
        ADMIN_REJECTED = "ADMIN_REJECTED", "Rejetée par l’équipe"
        EDITED = "EDITED", "Modifiée"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="detected_items",
    )

    # IMPORTANT: BatchUpload et MediaAsset sont dans mediahub
    batch = models.ForeignKey(
        "mediahub.BatchUpload",
        on_delete=models.CASCADE,
        related_name="detected_items",
    )

    hero_asset = models.ForeignKey(
        "mediahub.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hero_for_items",
    )
    listing = models.OneToOneField(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_item",
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Suggestions IA (persistées, jamais recalculées sans raison)
    title_suggested = models.CharField(max_length=120, blank=True, default="")
    description_suggested = models.TextField(blank=True, default="")
    category_suggested = models.CharField(max_length=64, blank=True, default="")

    price_low = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    price_high = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    confidence = models.FloatField(null=True, blank=True)

    # Tout ce que renvoie l'IA (bbox, labels, embeddings, etc.)
    metadata_json = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["batch", "status", "created_at"]),
            models.Index(fields=["owner", "status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"DetectedItem({self.id}) {self.status} - {self.title_suggested[:30]}"
