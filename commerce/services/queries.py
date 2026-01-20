# commerce/services/queries.py
from commerce.models import Order


def list_orders_for_user(*, user):
    return Order.objects.filter(buyer=user).order_by("-created_at")


def list_sales_for_user(*, user):
    return Order.objects.filter(seller=user).order_by("-created_at")


def get_active_order_for_listing(*, listing):
    return (
        Order.objects.filter(listing=listing)
        .exclude(
            status__in=[
                Order.Status.CANCELLED,
                Order.Status.EXPIRED,
                Order.Status.COMPLETED,
            ]
        )
        .first()
    )
