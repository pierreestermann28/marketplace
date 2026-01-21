# ingestion/services/publishing.py
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.db import transaction
from django.utils.text import slugify

from billing.entitlements import ensure_listing_quota, record_listing_publication
from catalog.services import find_category_by_slug_or_name
from ingestion.models import BatchMedia, DetectedItem
from listings.models import Listing, ListingImage


@transaction.atomic
def publish_detected_item(item: DetectedItem, skip_quota: bool = False) -> Listing:
    price_cents = _price_to_cents(item)
    category = _resolve_category(item.category_suggested)

    if not skip_quota:
        ensure_listing_quota(item.owner)

    listing = Listing(
        seller=item.owner,
        title=item.title_suggested_canonical or "Objet détecté",
        description=item.description_suggested_canonical or "",
        category=category,
        price_cents=price_cents,
        currency="EUR",
        status=Listing.Status.PUBLISHED,
        source_type=(
            "video"
            if item.hero_asset
            and item.hero_asset.media_type == BatchMedia.MediaType.VIDEO
            else "images"
        ),
        ai_summary={
            "confidence": item.confidence_canonical,
            "metadata": item.metadata_canonical or {},
        },
        source_item=item,
    )
    listing.save()
    record_listing_publication(item.owner)

    hero_asset = item.hero_asset
    if hero_asset:
        ListingImage.objects.create(
            listing=listing,
            image_asset=hero_asset.image_asset,  # mediahub.ImageAsset
            is_primary=True,
            sort_order=0,
        )

    return listing


def _price_to_cents(item: DetectedItem):
    price_candidate = item.price_low_canonical or item.price_high_canonical
    if price_candidate is None:
        return None
    try:
        price = Decimal(price_candidate)
    except (InvalidOperation, TypeError):
        return None
    cents = int((price * Decimal("100")).quantize(Decimal("1")))
    return max(cents, 1)


def _resolve_category(suggestion: Optional[str]):
    if not suggestion:
        return None
    normalized = suggestion.strip()
    if not normalized:
        return None
    return find_category_by_slug_or_name(normalized)
