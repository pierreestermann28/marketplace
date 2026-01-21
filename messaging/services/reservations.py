from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from django.conf import settings

from listings.models import Listing, Offer, OfferLog


class ReservationError(Exception):
    pass


@transaction.atomic
def create_reservation_from_conversation(*, conversation, note: str = "") -> None:
    listing = conversation.listing
    if listing.status != Listing.Status.PUBLISHED:
        raise ReservationError("Listing must be published")
    if Offer.objects.active().filter(listing=listing).exists():
        raise ReservationError("Active reservation already exists")

    expires_at = timezone.now() + timedelta(
        hours=getattr(settings, "RESERVATION_HOLD_HOURS", 24)
    )
    offer = Offer.objects.create(
        listing=listing,
        buyer=conversation.buyer,
        offer_price_cents=listing.price_cents or 0,
        currency=listing.currency,
        expires_at=expires_at,
        note=note,
    )
    OfferLog.objects.create(
        offer=offer,
        user=conversation.seller,
        action=OfferLog.Action.RESERVED,
        note=note,
    )
