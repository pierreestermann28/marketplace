from django.db import transaction

from listings.models import Listing
from listings.queries.reservations import get_active_reservation_offer
from listings.services.offers import (
    accept_offer,
    cancel_offer,
    OfferError,
)


class ReservationError(Exception):
    pass


class ReservationNotFound(ReservationError):
    pass


class ReservationInvalid(ReservationError):
    pass


def _ensure_seller(listing: Listing, user):
    if listing.seller_id != user.id:
        raise ReservationError("Utilisateur non autorisé.")


@transaction.atomic
def cancel_reservation(*, listing: Listing, seller) -> None:
    _ensure_seller(listing, seller)
    reservation = get_active_reservation_offer(listing)
    if not reservation:
        raise ReservationNotFound()
    try:
        cancel_offer(offer=reservation, buyer=reservation.buyer)
    except OfferError as exc:
        raise ReservationError(str(exc)) from exc


@transaction.atomic
def accept_reservation(*, listing: Listing, seller, note: str = "") -> None:
    _ensure_seller(listing, seller)
    reservation = get_active_reservation_offer(listing)
    if not reservation:
        raise ReservationNotFound()
    try:
        accept_offer(offer=reservation, seller=seller)
    except OfferError as exc:
        raise ReservationInvalid(str(exc)) from exc
    if note:
        reservation.note = note
        reservation.save(update_fields=["note"])
