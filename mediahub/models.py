import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone



class BatchUpload(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
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
    media_count = models.PositiveIntegerField(default=0)
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

    def mark_processing(self):
        self.status = self.Status.PROCESSING
        self.processing_started_at = timezone.now()
        self.save(update_fields=["status", "processing_started_at", "updated_at"])

    def mark_done(self):
        self.status = self.Status.DONE
        self.processed_at = timezone.now()
        self.save(update_fields=["status", "processed_at", "updated_at"])

    def mark_failed(self, message=None):
        self.status = self.Status.FAILED
        self.error_message = message or ""
        self.save(update_fields=["status", "error_message", "updated_at"])


class ImageAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="image_assets"
    )
    image = models.ImageField(upload_to="images/%Y/%m/%d/")
    source = models.CharField(max_length=20, default="upload")  # upload|keyframe|other
    created_at = models.DateTimeField(auto_now_add=True)


class MediaAsset(models.Model):
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
        related_name="media_asset",
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
    file_hash = models.CharField(max_length=64, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.media_type.upper()} #{self.id}"


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
