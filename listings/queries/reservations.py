from django.db.models import Prefetch

from listings.models import Offer

ACTIVE_RESERVATION_PREFETCH = Prefetch(
    "offers",
    queryset=Offer.objects.active().select_related("buyer"),
    to_attr="active_reservations",
)


def get_active_reservation_offer(listing):
    reservations = getattr(listing, "active_reservations", None)
    if reservations is not None:
        return reservations[0] if reservations else None
    return (
        Offer.objects.active()
        .filter(listing=listing)
        .select_related("buyer")
        .first()
    )
