from collections import defaultdict
from typing import Dict, Iterable, List

from django.db.models import Count, Q

from billing.models import UserEntitlement
from commerce.models import Order
from ingestion.models import BatchUpload, DetectedItem
from listings.models import Listing


def get_operation_counts(limit_trending: int = 6) -> Dict[str, object]:
    return {
        "orders_pending": Order.objects.filter(
            status__in=[Order.Status.CREATED, Order.Status.AWAITING_CONFIRMATION]
        ).count(),
        "orders_attention": Order.objects.filter(
            status__in=[Order.Status.EXPIRED, Order.Status.CANCELLED]
        ).count(),
        "pending_detected_items": DetectedItem.objects.filter(
            status=DetectedItem.Status.PENDING
        ).count(),
        "trending_listings": _get_trending_listings(limit_trending),
    }


def _get_trending_listings(limit: int) -> List[Listing]:
    return list(
        Listing.objects.filter(status=Listing.Status.PUBLISHED)
        .order_by("-view_count")
        .select_related("seller")
        .prefetch_related("images")
        .all()[: max(0, limit)]
    )


def get_recent_batch_summaries(limit: int = 5) -> List[Dict[str, object]]:
    batches = list(
        BatchUpload.objects.select_related("owner")
        .order_by("-created_at")
        .all()[: max(0, limit)]
    )
    if not batches:
        return []
    batch_ids = [batch.id for batch in batches]
    counts = _batch_detected_counts(batch_ids)
    summaries = []
    for batch in batches:
        stats = counts.get(batch.id, {})
        ready = stats.get(DetectedItem.Status.USER_APPROVED, 0) + stats.get(
            DetectedItem.Status.ADMIN_APPROVED, 0
        )
        pending = stats.get(DetectedItem.Status.PENDING, 0)
        others = sum(
            value
            for status, value in stats.items()
            if status
            not in {
                DetectedItem.Status.PENDING,
                DetectedItem.Status.USER_APPROVED,
                DetectedItem.Status.ADMIN_APPROVED,
            }
        )
        summaries.append(
            {
                "batch": batch,
                "pending": pending,
                "ready": ready,
                "others": others,
                "total_detected": sum(stats.values()),
            }
        )
    return summaries


def _batch_detected_counts(batch_ids: Iterable) -> Dict[object, Dict[str, int]]:
    if not batch_ids:
        return {}
    data = (
        DetectedItem.objects.filter(batch_id__in=batch_ids)
        .values("batch_id", "status")
        .annotate(count=Count("id"))
    )
    counts: Dict[object, Dict[str, int]] = defaultdict(dict)
    for entry in data:
        counts[entry["batch_id"]][entry["status"]] = entry["count"]
    return counts


def get_pending_review_listings(limit: int = 6):
    return (
        Listing.objects.filter(
            Q(status=Listing.Status.PENDING_REVIEW) | Q(needs_review=True)
        )
        .select_related("seller", "category")
        .order_by("created_at")[: max(0, limit)]
    )


def get_recent_entitlements(limit: int = 6):
    return (
        UserEntitlement.objects.select_related("user")
        .order_by("-updated_at")
        .all()[: max(0, limit)]
    )
