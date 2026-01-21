import uuid

from django.conf import settings
from django.db import models


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
