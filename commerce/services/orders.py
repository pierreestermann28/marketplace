# commerce/services/orders.py
import secrets
from django.db import transaction
from django.utils import timezone

from commerce.models import Order


class InvalidOrderTransition(Exception):
    pass


@transaction.atomic
def create_order_from_listing(
    *,
    listing,
    buyer,
    fulfillment: str,
    proposed_price_cents: int | None = None,
    buyer_address=None,
    seller_address=None,
) -> Order:
    seller = listing.seller

    order = Order.objects.create(
        listing=listing,
        buyer=buyer,
        seller=seller,
        fulfillment=fulfillment,
        status=Order.Status.CREATED,
        proposed_price_cents=proposed_price_cents,
        buyer_address=buyer_address,
        seller_address=seller_address,
        handover_code=(
            _generate_handover_code()
            if fulfillment == Order.Fulfillment.IN_PERSON
            else ""
        ),
    )
    return order


@transaction.atomic
def cancel_order(*, order: Order, by_user, reason: str = "") -> None:
    if order.status in (
        Order.Status.COMPLETED,
        Order.Status.CANCELLED,
        Order.Status.EXPIRED,
    ):
        return
    # (option) check permissions: buyer or seller
    if by_user.id not in (order.buyer_id, order.seller_id):
        raise PermissionError("Not allowed")

    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def expire_order(*, order: Order) -> None:
    if order.status in (
        Order.Status.COMPLETED,
        Order.Status.CANCELLED,
        Order.Status.EXPIRED,
    ):
        return
    order.status = Order.Status.EXPIRED
    order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def schedule_meetup(*, order: Order, deadline_at=None) -> None:
    if order.fulfillment != Order.Fulfillment.IN_PERSON:
        raise InvalidOrderTransition("Not an in-person order")
    if order.status not in (Order.Status.CREATED, Order.Status.MEETUP_SCHEDULED):
        raise InvalidOrderTransition("Cannot schedule meetup now")

    order.status = Order.Status.MEETUP_SCHEDULED
    if deadline_at is not None:
        order.confirmation_deadline = deadline_at
    order.save(update_fields=["status", "confirmation_deadline", "updated_at"])


@transaction.atomic
def mark_in_transit(*, order: Order, deadline_at=None) -> None:
    if order.fulfillment != Order.Fulfillment.SHIPPING:
        raise InvalidOrderTransition("Not a shipping order")
    if order.status not in (Order.Status.CREATED, Order.Status.IN_TRANSIT):
        raise InvalidOrderTransition("Cannot mark in transit now")

    order.status = Order.Status.IN_TRANSIT
    if deadline_at is not None:
        order.confirmation_deadline = deadline_at
    order.save(update_fields=["status", "confirmation_deadline", "updated_at"])


@transaction.atomic
def request_confirmation(*, order: Order, deadline_at=None) -> None:
    if order.status not in (Order.Status.MEETUP_SCHEDULED, Order.Status.IN_TRANSIT):
        raise InvalidOrderTransition("Cannot request confirmation now")
    order.status = Order.Status.AWAITING_CONFIRMATION
    if deadline_at is not None:
        order.confirmation_deadline = deadline_at
    order.save(update_fields=["status", "confirmation_deadline", "updated_at"])


@transaction.atomic
def confirm_handover(*, order: Order, by_user, code: str | None = None) -> None:
    if order.status not in (
        Order.Status.MEETUP_SCHEDULED,
        Order.Status.AWAITING_CONFIRMATION,
    ):
        raise InvalidOrderTransition("Cannot confirm now")

    # Permission: buyer confirms receipt / handover (you can choose seller too)
    if by_user.id != order.buyer_id:
        raise PermissionError("Only buyer can confirm")

    # If in-person, verify code (optional)
    if order.fulfillment == Order.Fulfillment.IN_PERSON and order.handover_code:
        if (code or "").strip() != order.handover_code:
            raise PermissionError("Invalid handover code")

    order.handover_confirmed_at = timezone.now()
    order.status = Order.Status.COMPLETED
    order.save(update_fields=["handover_confirmed_at", "status", "updated_at"])


def _generate_handover_code() -> str:
    # 6–10 chars, simple, no ambiguous chars if you want
    return secrets.token_hex(3).upper()
