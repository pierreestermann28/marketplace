"""Read-only query helpers for seller dashboard/listing summaries."""

from typing import Dict, Iterable

from django.db.models import Count, QuerySet

from listings.models import Listing
from listings.queries.reservations import ACTIVE_RESERVATION_PREFETCH


def get_my_listings_queryset(
    user, status_filter: Iterable[str] | None = None
) -> QuerySet[Listing]:
    """Return the queryset for a seller's own listings."""
    qs = (
        Listing.objects.filter(seller=user)
        .select_related("category")
        .prefetch_related("images__image_asset", ACTIVE_RESERVATION_PREFETCH)
        .order_by("-updated_at")
    )
    if status_filter:
        qs = qs.filter(status__in=status_filter)
    return qs


def get_listing_status_counts(user) -> Dict[str, int]:
    """Return a mapping of listing status -> count for the given seller."""
    counts = (
        Listing.objects.filter(seller=user)
        .values("status")
        .annotate(count=Count("status"))
    )
    return {row["status"]: row["count"] for row in counts}
