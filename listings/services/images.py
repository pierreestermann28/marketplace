# listings/services/images.py
from django.db import transaction
from django.db.models import Max

from mediahub.services import create_image_asset

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


def _normalize_primary_index(primary_index: int, total: int) -> int:
    if total <= 0:
        return 0
    if primary_index < 0:
        return 0
    if primary_index >= total:
        return total - 1
    return primary_index


@transaction.atomic
def attach_listing_images(
    *,
    listing: Listing,
    images,
    primary_index: int = 0,
) -> None:
    if not images:
        return
    for idx, image in enumerate(images):
        asset = create_image_asset(user=listing.seller, image=image)
        ListingImage.objects.create(
            listing=listing,
            image_asset=asset,
            is_primary=False,
            sort_order=idx,
        )
    _set_sort_and_primary(listing=listing, primary_index=primary_index)


def _set_sort_and_primary(*, listing: Listing, primary_index: int) -> None:
    listing_images = list(
        listing.images.select_related("image_asset").order_by(
            "sort_order", "created_at"
        )
    )
    if not listing_images:
        return
    final_index = _normalize_primary_index(primary_index, len(listing_images))
    for idx, listing_image in enumerate(listing_images):
        listing_image.sort_order = idx
        listing_image.is_primary = idx == final_index
        listing_image.save(update_fields=["sort_order", "is_primary"])


@transaction.atomic
def add_images_to_listing(*, listing: Listing, images) -> None:
    if not images:
        return
    max_order = listing.images.aggregate(max_order=Max("sort_order"))["max_order"]
    next_order = (max_order + 1) if max_order is not None else 0
    for image in images:
        asset = create_image_asset(user=listing.seller, image=image)
        ListingImage.objects.create(
            listing=listing,
            image_asset=asset,
            sort_order=next_order,
            is_primary=False,
        )
        next_order += 1
