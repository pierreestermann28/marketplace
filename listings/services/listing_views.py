# listings/services/views.py
from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone

from listings.models import Listing, ListingView


def record_listing_view(*, listing: Listing, user) -> None:
    """
    - enregistre une vue unique (user, listing)
    - incrémente view_count uniquement la première fois
    """
    if not user or not getattr(user, "is_authenticated", False):
        Listing.objects.filter(pk=listing.pk).update(view_count=F("view_count") + 1)
        return

    try:
        ListingView.objects.create(user=user, listing=listing, viewed_at=timezone.now())
    except IntegrityError:
        # déjà vu
        return

    Listing.objects.filter(pk=listing.pk).update(view_count=F("view_count") + 1)
