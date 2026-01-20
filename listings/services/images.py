# listings/services/images.py
from django.db import transaction

from listings.models import Listing, ListingImage


def get_primary_image(*, listing: Listing):
    primary = (
        listing.images.filter(is_primary=True).select_related("image_asset").first()
    )
    return (
        primary
        or listing.images.select_related("image_asset").order_by("sort_order").first()
    )


@transaction.atomic
def set_primary_image(*, listing: Listing, listing_image: ListingImage) -> None:
    ListingImage.objects.filter(listing=listing, is_primary=True).update(
        is_primary=False
    )
    ListingImage.objects.filter(pk=listing_image.pk, listing=listing).update(
        is_primary=True
    )
