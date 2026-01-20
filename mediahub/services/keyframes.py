# mediahub/services/keyframes.py
from django.db import transaction

from mediahub.models import Keyframe, VideoUpload


@transaction.atomic
def create_keyframe(
    *,
    video: VideoUpload,
    image,
    timestamp_ms: int,
    sharpness_score: float = 0.0,
) -> Keyframe:
    return Keyframe.objects.create(
        video=video,
        image=image,
        timestamp_ms=max(0, int(timestamp_ms)),
        sharpness_score=sharpness_score,
    )


@transaction.atomic
def deselect_all_keyframes(*, video: VideoUpload) -> int:
    return Keyframe.objects.filter(video=video, is_selected=True).update(
        is_selected=False
    )


@transaction.atomic
def select_top_keyframes(*, video: VideoUpload, max_count: int = 5) -> int:
    """
    Sélectionne les N keyframes les plus nettes.
    Retourne le nombre sélectionné.
    """
    deselect_all_keyframes(video=video)

    selected = Keyframe.objects.filter(video=video).order_by(
        "-sharpness_score", "timestamp_ms"
    )[: max(0, int(max_count))]
    ids = [k.id for k in selected]
    if not ids:
        return 0
    return Keyframe.objects.filter(id__in=ids).update(is_selected=True)


def get_selected_keyframes(*, video: VideoUpload):
    return Keyframe.objects.filter(video=video, is_selected=True).order_by(
        "timestamp_ms"
    )
