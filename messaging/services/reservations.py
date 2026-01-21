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
    Offer.objects.create(
        listing=listing,
        buyer=conversation.buyer,
        expires_at=expires_at,
    )
    listing.status = Listing.Status.RESERVED
    listing.reserved_for = conversation.buyer
    listing.reserved_at = timezone.now()
    listing.reservation_note = note
    listing.save(
        update_fields=[
            "status",
            "reserved_for",
            "reserved_at",
            "reservation_note",
            "updated_at",
        ]
    )
    OfferLog.objects.create(
        listing=listing,
        user=conversation.seller,
        action=OfferLog.Action.RESERVED,
        note=note,
    )
