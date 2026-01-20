# ingestion/models.py
import uuid

from django.conf import settings
from django.db import models

from mediahub.models import ImageAsset


class BatchUpload(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        DONE = "DONE", "Done"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="batch_uploads",
    )

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    sale_location = models.CharField(max_length=140, blank=True, db_index=True)
    seller_notes = models.TextField(blank=True)

    media_count = models.PositiveIntegerField(default=0)
    processed_count = models.PositiveIntegerField(default=0)

    processing_started_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "status", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]


class BatchMedia(models.Model):
    class Source(models.TextChoices):
        UPLOAD = "upload", "Upload"
        KEYFRAME = "keyframe", "Keyframe"
        OTHER = "other", "Other"

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    batch = models.ForeignKey(
        BatchUpload,
        on_delete=models.CASCADE,
        related_name="media_assets",
    )

    image_asset = models.OneToOneField(
        ImageAsset,
        on_delete=models.CASCADE,
        related_name="ingestion_media_asset",
    )

    media_type = models.CharField(
        max_length=12,
        choices=MediaType.choices,
        default=MediaType.IMAGE,
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.UPLOAD,
    )

    file_hash = models.CharField(max_length=64, blank=True, db_index=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["batch", "created_at"]),
            models.Index(fields=["batch", "source", "created_at"]),
            models.Index(fields=["file_hash"]),
        ]

    def __str__(self):
        return f"{self.media_type.upper()} #{self.id}"


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

    # ✅ pointe vers ingestion.BatchUpload (source de vérité “batch IA”)
    batch = models.ForeignKey(
        BatchUpload,
        on_delete=models.CASCADE,
        related_name="detected_items",
    )

    hero_asset = models.ForeignKey(
        BatchMedia,
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
        # ⚠️ évite de référencer un champ possiblement absent si ton snippet est tronqué
        return f"DetectedItem({self.id}) {self.status}"
