import uuid
from django.conf import settings
from django.db import models


class ImageAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="image_assets"
    )
    image = models.ImageField(upload_to="images/%Y/%m/%d/")
    source = models.CharField(max_length=20, default="upload")  # upload|keyframe|other
    created_at = models.DateTimeField(auto_now_add=True)


# --- Future ready (tu peux commenter pour V1 si tu veux) ---


class VideoUpload(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded"
        PROCESSING = "processing"
        READY = "ready"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_uploads"
    )

    file = models.FileField(upload_to="videos/%Y/%m/%d/")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.UPLOADED, db_index=True
    )
    error_message = models.TextField(blank=True)

    duration_s = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)


class Keyframe(models.Model):
    video = models.ForeignKey(
        VideoUpload, on_delete=models.CASCADE, related_name="keyframes"
    )
    image = models.ImageField(upload_to="keyframes/%Y/%m/%d/")
    timestamp_ms = models.PositiveIntegerField(db_index=True)

    sharpness_score = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    is_selected = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("video", "timestamp_ms")]
        indexes = [
            models.Index(fields=["video", "is_selected"]),
            models.Index(fields=["video", "timestamp_ms"]),
        ]
