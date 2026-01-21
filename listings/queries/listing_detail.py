"""Read-only query helpers for listing detail views."""

from django.db.models import BooleanField, Exists, OuterRef, QuerySet, Value

from listings.models import Favorite, Listing
from listings.queries.reservations import ACTIVE_RESERVATION_PREFETCH


def _detail_status_filter() -> list[str]:
    return [Listing.Status.PUBLISHED]


def build_listing_detail_queryset(user) -> QuerySet[Listing]:
    """Return the queryset used by listing detail pages."""
    qs: QuerySet[Listing] = Listing.objects.filter(status__in=_detail_status_filter())
    if user and getattr(user, "is_authenticated", False):
        qs = qs.annotate(
            is_favorited=Exists(
                Favorite.objects.filter(user=user, listing=OuterRef("pk"))
            )
        )
    else:
        qs = qs.annotate(is_favorited=Value(False, output_field=BooleanField()))

    return (
        qs.select_related("category", "seller")
        .prefetch_related("images__image_asset", ACTIVE_RESERVATION_PREFETCH)
    )
