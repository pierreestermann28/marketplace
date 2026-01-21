# listings/services/reservations.py
from django.db import transaction

from listings.models import Listing, OfferLog


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
    reservation = listing.refresh_reservation_state()
    if not reservation:
        raise ReservationNotFound()
    reservation.cancel()


@transaction.atomic
def accept_reservation(*, listing: Listing, seller, note: str = "") -> None:
    _ensure_seller(listing, seller)
    reservation = listing.refresh_reservation_state()
    if not reservation:
        raise ReservationNotFound()
    if listing.status != Listing.Status.RESERVED:
        raise ReservationInvalid("Le statut de l'annonce ne permet pas d'accepter la réservation.")
    listing.status = Listing.Status.RESERVATION_ACCEPTED
    listing.save(update_fields=["status"])
    OfferLog.objects.create(
        listing=listing,
        user=seller,
        action=OfferLog.Action.ACCEPTED,
        note=note or "Acceptation manuelle.",
    )
