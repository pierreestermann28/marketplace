# ingestion/services/items.py
from django.db import transaction

from ingestion.models import DetectedItem


@transaction.atomic
def user_approve(*, item: DetectedItem) -> None:
    item.status = DetectedItem.Status.USER_APPROVED
    item.save(update_fields=["status", "updated_at"])


@transaction.atomic
def user_reject(*, item: DetectedItem) -> None:
    item.status = DetectedItem.Status.USER_REJECTED
    item.save(update_fields=["status", "updated_at"])


@transaction.atomic
def admin_approve(*, item: DetectedItem) -> None:
    item.status = DetectedItem.Status.ADMIN_APPROVED
    item.save(update_fields=["status", "updated_at"])


@transaction.atomic
def admin_reject(*, item: DetectedItem) -> None:
    item.status = DetectedItem.Status.ADMIN_REJECTED
    item.save(update_fields=["status", "updated_at"])
