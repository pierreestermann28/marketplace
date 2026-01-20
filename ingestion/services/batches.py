# ingestion/services/batches.py
import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from ingestion.models import BatchUpload


logger = logging.getLogger("ingestion.batch")


@transaction.atomic
def mark_processing(*, batch: BatchUpload) -> None:
    batch.status = BatchUpload.Status.RUNNING
    batch.processing_started_at = timezone.now()
    batch.processed_count = 0
    batch.error_message = ""
    batch.save(
        update_fields=[
            "status",
            "processing_started_at",
            "processed_count",
            "error_message",
            "updated_at",
        ]
    )
    logger.info(
        "Batch processing started",
        extra={"batch_id": str(batch.id), "owner_id": batch.owner_id},
    )


@transaction.atomic
def mark_done(*, batch: BatchUpload) -> None:
    batch.status = BatchUpload.Status.DONE
    batch.processed_at = timezone.now()
    batch.save(update_fields=["status", "processed_at", "updated_at"])
    logger.info(
        "Batch processing completed",
        extra={"batch_id": str(batch.id), "owner_id": batch.owner_id},
    )


@transaction.atomic
def mark_failed(*, batch: BatchUpload, message: str | None = None) -> None:
    batch.status = BatchUpload.Status.FAILED
    batch.error_message = message or ""
    batch.save(update_fields=["status", "error_message", "updated_at"])
    logger.error(
        "Batch processing failed",
        extra={
            "batch_id": str(batch.id),
            "owner_id": batch.owner_id,
            "error_message": batch.error_message,
        },
    )


def increment_processed_count(*, batch: BatchUpload) -> int:
    BatchUpload.objects.filter(pk=batch.pk).update(
        processed_count=F("processed_count") + 1
    )
    batch.refresh_from_db(fields=["processed_count"])
    return batch.processed_count


def progress_percentage(*, batch: BatchUpload) -> int:
    if not batch.media_count:
        return 0
    return min(100, int(round((batch.processed_count / batch.media_count) * 100, 0)))


@transaction.atomic
def reset_for_retry(*, batch: BatchUpload) -> None:
    batch.detected_items.all().delete()
    batch.status = BatchUpload.Status.PENDING
    batch.processed_count = 0
    batch.processing_started_at = None
    batch.processed_at = None
    batch.error_message = ""
    batch.save(
        update_fields=[
            "status",
            "processed_count",
            "processing_started_at",
            "processed_at",
            "error_message",
            "updated_at",
        ]
    )
