from decimal import Decimal, InvalidOperation
from typing import Optional

from catalog.models import Category
from django.utils.text import slugify
from listings.models import Listing, ListingImage

from ..models import DetectedItem
from mediahub.models import MediaAsset


def publish_detected_item(item: DetectedItem) -> Listing:
    price_cents = _price_to_cents(item)
    category = _resolve_category(item.category_suggested)
    listing = Listing(
        seller=item.owner,
        title=item.title_suggested or "Objet détecté",
        description=item.description_suggested or "",
        category=category,
        price_cents=price_cents,
        currency="EUR",
        status=Listing.Status.PUBLISHED,
        source_type="video"
        if item.hero_asset
        and item.hero_asset.media_type == MediaAsset.MediaType.VIDEO
        else "images",
        ai_summary={
            "confidence": item.confidence,
            "metadata": item.metadata_json or {},
        },
    )
    listing.save()

    hero_asset = item.hero_asset
    if hero_asset:
        ListingImage.objects.create(
            listing=listing,
            image_asset=hero_asset.image_asset,
            is_primary=True,
            sort_order=0,
        )
    return listing


def _price_to_cents(item: DetectedItem):
    price_candidate = item.price_low or item.price_high
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
    slug = slugify(normalized)
    category = None
    if slug:
        category = Category.objects.filter(slug__iexact=slug).first()
    if not category:
        category = Category.objects.filter(name__iexact=normalized).first()
    return category
