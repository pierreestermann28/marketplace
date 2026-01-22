import uuid

from django.conf import settings
from django.db import models
from django.db.models import F


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

    def mark_asset_processed(self, *, commit=True):
        self.processed_count = F("processed_count") + 1
        self.save(update_fields=["processed_count"])
        self.refresh_from_db(fields=["processed_count"])
