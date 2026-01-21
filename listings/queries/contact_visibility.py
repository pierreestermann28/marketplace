from typing import Optional

from django.contrib.auth import get_user_model

from listings.models import Listing


def user_can_view_contact_info(
    user: Optional[get_user_model()], listing: Listing
) -> bool:
    if not user or not user.is_authenticated:
        return False
    if listing.seller == user:
        return True
    if listing.offers.active().filter(buyer=user).exists():
        return True
    try:
        from commerce.models import Order
    except ImportError:
        return False

    unlocked_statuses = {
        Order.Status.PAID,
        Order.Status.MEETUP_SCHEDULED,
        Order.Status.LABEL_READY,
        Order.Status.IN_TRANSIT,
        Order.Status.AWAITING_CONFIRMATION,
        Order.Status.COMPLETED,
    }
    return Order.objects.filter(
        listing=listing, buyer=user, status__in=unlocked_statuses
    ).exists()
