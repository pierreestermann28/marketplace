from typing import Optional

from django.contrib.auth import get_user_model

from .models import Listing


def user_can_message_listing(user: Optional[get_user_model()], listing: Listing) -> bool:
    if not user or not user.is_authenticated:
        return False
    if listing.seller == user:
        return True
    if listing.reservations.filter(buyer=user, cancelled_at__isnull=True).exists():
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
