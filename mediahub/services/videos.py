# mediahub/services/videos.py
from django.db import transaction

from mediahub.models import VideoUpload


@transaction.atomic
def create_video_upload(*, user, file) -> VideoUpload:
    return VideoUpload.objects.create(
        user=user, file=file, status=VideoUpload.Status.UPLOADED
    )


@transaction.atomic
def mark_video_processing(*, video: VideoUpload) -> None:
    video.status = VideoUpload.Status.PROCESSING
    video.error_message = ""
    video.save(update_fields=["status", "error_message"])


@transaction.atomic
def mark_video_ready(
    *, video: VideoUpload, duration_s: int, width: int, height: int
) -> None:
    video.status = VideoUpload.Status.READY
    video.duration_s = max(0, int(duration_s))
    video.width = max(0, int(width))
    video.height = max(0, int(height))
    video.save(update_fields=["status", "duration_s", "width", "height"])


@transaction.atomic
def mark_video_failed(*, video: VideoUpload, error_message: str) -> None:
    video.status = VideoUpload.Status.FAILED
    video.error_message = error_message or ""
    video.save(update_fields=["status", "error_message"])
