# listings/services/listing_creation.py
from __future__ import annotations

from django.db import transaction

from listings.models import Listing

from .images import attach_listing_images


@transaction.atomic
def create_listing_with_images(
    *,
    seller,
    images,
    primary_index: int = 0,
    currency: str = "EUR",
) -> Listing:
    listing = Listing.objects.create(
        seller=seller,
        status=Listing.Status.DRAFT,
        currency=currency,
    )
    attach_listing_images(
        listing=listing,
        images=images,
        primary_index=primary_index,
    )
    return listing

