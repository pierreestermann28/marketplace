# ingestion/services/media.py
import hashlib
from django.db import transaction

from ingestion.models import BatchMedia, BatchUpload


@transaction.atomic
def create_batch_media(
    *,
    batch: BatchUpload,
    image_asset,
    media_type: str = BatchMedia.MediaType.IMAGE,
    source: str = BatchMedia.Source.UPLOAD,
    file_hash: str = "",
    metadata_json: dict | None = None,
) -> BatchMedia:
    media = BatchMedia.objects.create(
        batch=batch,
        image_asset=image_asset,
        media_type=media_type,
        source=source,
        file_hash=file_hash,
        metadata_json=metadata_json or {},
    )
    return media


def compute_file_hash_sha256(file_obj) -> str:
    """
    file_obj: FileField ou UploadedFile (doit fournir chunks()).
    """
    h = hashlib.sha256()
    for chunk in file_obj.chunks():
        h.update(chunk)
    return h.hexdigest()


@transaction.atomic
def set_batch_media_hash(*, media: BatchMedia, file_hash: str) -> None:
    media.file_hash = file_hash
    media.save(update_fields=["file_hash"])


@transaction.atomic
def set_batch_media_metadata(*, media: BatchMedia, metadata_json: dict) -> None:
    media.metadata_json = metadata_json or {}
    media.save(update_fields=["metadata_json"])
