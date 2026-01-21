import uuid

from django.db import models

from mediahub.models import ImageAsset


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
        "ingestion.BatchUpload",
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
