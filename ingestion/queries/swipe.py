from typing import Dict

from ingestion.models import DetectedItem


def get_user_pending_items(user):
    return (
        DetectedItem.objects.filter(owner=user, status=DetectedItem.Status.PENDING)
        .select_related("hero_asset__image_asset")
        .order_by("created_at")
    )


def get_next_user_item(user):
    return get_user_pending_items(user).first()


def get_next_admin_item():
    return (
        DetectedItem.objects.filter(status=DetectedItem.Status.USER_APPROVED)
        .select_related("owner", "batch", "hero_asset__image_asset")
        .order_by("updated_at")
        .first()
    )


def get_admin_counts() -> Dict[str, int]:
    return {
        "pending_admin_count": DetectedItem.objects.filter(
            status=DetectedItem.Status.USER_APPROVED
        ).count(),
        "pending_user_count": DetectedItem.objects.filter(
            status=DetectedItem.Status.PENDING
        ).count(),
    }
