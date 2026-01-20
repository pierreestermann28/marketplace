# mediahub/models.py
import uuid

from django.conf import settings
from django.db import models


class ImageAsset(models.Model):
    class Source(models.TextChoices):
        UPLOAD = "upload", "Upload"
        KEYFRAME = "keyframe", "Keyframe"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="image_assets",
    )

    image = models.ImageField(upload_to="images/%Y/%m/%d/")
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.UPLOAD
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["source", "created_at"]),
        ]


class VideoUpload(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="video_uploads",
    )

    file = models.FileField(upload_to="videos/%Y/%m/%d/")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.UPLOADED,
        db_index=True,
    )
    error_message = models.TextField(blank=True)

    duration_s = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]


class Keyframe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    video = models.ForeignKey(
        VideoUpload,
        on_delete=models.CASCADE,
        related_name="keyframes",
    )

    image = models.ImageField(upload_to="keyframes/%Y/%m/%d/")
    timestamp_ms = models.PositiveIntegerField(db_index=True)

    sharpness_score = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    is_selected = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["video", "timestamp_ms"],
                name="uniq_keyframe_video_timestamp",
            )
        ]
        indexes = [
            models.Index(fields=["video", "is_selected"]),
            models.Index(fields=["video", "timestamp_ms"]),
            models.Index(fields=["video", "-sharpness_score"]),
        ]
