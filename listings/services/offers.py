# listings/services/offers.py
from __future__ import annotations

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from listings.models import Listing, Offer, OfferLog


class OfferError(Exception):
    pass


class OfferNotAllowed(OfferError):
    pass


class OfferExpired(OfferError):
    pass


@transaction.atomic
def make_offer(
    *,
    listing: Listing,
    buyer,
    offer_price_cents: int,
    note: str = "",
    ttl_hours: int = 6,
) -> Offer:
    if listing.status != Listing.Status.PUBLISHED:
        raise OfferNotAllowed("Listing is not available.")

    if listing.seller_id == buyer.id:
        raise OfferNotAllowed("You cannot make an offer on your own listing.")

    if offer_price_cents <= 0:
        raise OfferNotAllowed("Offer price must be positive.")

    expires_at = timezone.now() + timedelta(hours=ttl_hours)

    # One offer per buyer per listing -> update or create
    # Concurrency-safe: retry once if unique constraint races.
    try:
        offer, _created = Offer.objects.update_or_create(
            listing=listing,
            buyer=buyer,
            defaults={
                "offer_price_cents": offer_price_cents,
                "currency": listing.currency,
                "note": note,
                "status": Offer.Status.REQUESTED,
                "expires_at": expires_at,
                "cancelled_at": None,
                "decided_at": None,
                "decided_by": None,
            },
        )
    except IntegrityError:
        # Another transaction created it between SELECT and INSERT.
        offer = Offer.objects.select_for_update().get(listing=listing, buyer=buyer)
        offer.offer_price_cents = offer_price_cents
        offer.currency = listing.currency
        offer.note = note
        offer.status = Offer.Status.REQUESTED
        offer.expires_at = expires_at
        offer.cancelled_at = None
        offer.decided_at = None
        offer.decided_by = None
        offer.save(
            update_fields=[
                "offer_price_cents",
                "currency",
                "note",
                "status",
                "expires_at",
                "cancelled_at",
                "decided_at",
                "decided_by",
            ]
        )

    OfferLog.objects.create(
        offer=offer,
        user=buyer,
        action=OfferLog.Action.CREATED,
        note=note,
    )

    return offer


@transaction.atomic
def cancel_offer(*, offer: Offer, buyer) -> Offer:
    offer = Offer.objects.select_for_update().get(pk=offer.pk)

    if offer.buyer_id != buyer.id:
        raise OfferNotAllowed("Not your offer.")

    if offer.status in {Offer.Status.ACCEPTED, Offer.Status.REJECTED}:
        raise OfferNotAllowed("Offer already decided.")

    if offer.cancelled_at:
        return offer  # idempotent

    offer.status = Offer.Status.CANCELLED
    offer.cancelled_at = timezone.now()
    offer.save(update_fields=["status", "cancelled_at"])

    OfferLog.objects.create(
        offer=offer,
        user=buyer,
        action=OfferLog.Action.CANCELLED,
        note="",
    )
    return offer


@transaction.atomic
def accept_offer(*, offer: Offer, seller, reject_others: bool = True) -> Offer:
    # Lock offer + listing context
    offer = Offer.objects.select_for_update().select_related("listing").get(pk=offer.pk)
    listing = offer.listing

    if listing.seller_id != seller.id:
        raise OfferNotAllowed("Not the seller.")

    if listing.status != Listing.Status.PUBLISHED:
        raise OfferNotAllowed("Listing is not available anymore.")

    if offer.status != Offer.Status.REQUESTED or offer.cancelled_at is not None:
        raise OfferNotAllowed("Offer cannot be accepted (not in requested state).")

    if offer.is_expired():
        raise OfferExpired("Offer has expired.")

    # Prevent accepting if another offer already accepted
    already_accepted = (
        Offer.objects.select_for_update()
        .filter(
            listing=listing, status=Offer.Status.ACCEPTED, cancelled_at__isnull=True
        )
        .exclude(pk=offer.pk)
        .exists()
    )
    if already_accepted:
        raise OfferNotAllowed("Another offer is already accepted for this listing.")

    now = timezone.now()
    offer.status = Offer.Status.ACCEPTED
    offer.decided_at = now
    offer.decided_by = seller
    offer.save(update_fields=["status", "decided_at", "decided_by"])

    OfferLog.objects.create(
        offer=offer,
        user=seller,
        action=OfferLog.Action.ACCEPTED,
        note="",
    )

    if reject_others:
        Offer.objects.active().filter(listing=listing).exclude(pk=offer.pk).update(
            status=Offer.Status.REJECTED,
            decided_at=now,
            decided_by=seller,
        )

    return offer


@transaction.atomic
def reject_offer(*, offer: Offer, seller) -> Offer:
    offer = Offer.objects.select_for_update().select_related("listing").get(pk=offer.pk)
    listing = offer.listing

    if listing.seller_id != seller.id:
        raise OfferNotAllowed("Not the seller.")

    if offer.status != Offer.Status.REQUESTED or offer.cancelled_at is not None:
        raise OfferNotAllowed("Offer cannot be rejected.")

    if offer.is_expired():
        raise OfferExpired("Offer has expired.")

    now = timezone.now()
    offer.status = Offer.Status.REJECTED
    offer.decided_at = now
    offer.decided_by = seller
    offer.save(update_fields=["status", "decided_at", "decided_by"])

    OfferLog.objects.create(
        offer=offer,
        user=seller,
        action=OfferLog.Action.REJECTED,
        note="",
    )
    return offer
