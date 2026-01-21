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
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="detected_items",
    )

    batch = models.ForeignKey(
        "ingestion.BatchUpload",
        on_delete=models.CASCADE,
        related_name="detected_items",
    )

    hero_asset = models.ForeignKey(
        "ingestion.BatchMedia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hero_for_items",
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    current_suggestion = models.ForeignKey(
        "ai.AISuggestion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["batch", "status", "created_at"]),
            models.Index(fields=["owner", "status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"DetectedItem({self.id}) {self.status}"
