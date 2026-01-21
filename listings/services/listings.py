# listings/services/listings.py
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from listings.models import Listing, ListingChangeLog


@transaction.atomic
def create_listing(*, seller, **fields) -> Listing:
    listing = Listing(seller=seller, **fields)
    _prepare_listing_fields(listing)
    listing.save()
    return listing


@transaction.atomic
def update_listing(*, listing: Listing, user, **fields) -> Listing:
    for k, v in fields.items():
        setattr(listing, k, v)

    _prepare_listing_fields(listing)
    listing.save()

    record_listing_history(
        listing=listing,
        user=user,
        event=Listing.ChangeEvent.DETAILS_UPDATED,
        details=f"Updated fields: {', '.join(fields.keys())}",
    )
    return listing


@transaction.atomic
def submit_for_review(*, listing: Listing, user) -> Listing:
    if listing.status != Listing.Status.DRAFT:
        return listing

    listing.status = Listing.Status.PENDING_REVIEW
    listing.needs_review = True
    listing.available_from = timezone.now()
    listing.save(
        update_fields=["status", "needs_review", "available_from", "updated_at"]
    )

    record_listing_history(
        listing=listing,
        user=user,
        event=Listing.ChangeEvent.SUBMITTED,
        details="Submitted for review",
    )
    return listing


@transaction.atomic
def moderate_approve(*, listing: Listing, admin_user, notes: str = "") -> Listing:
    listing.status = Listing.Status.PUBLISHED
    listing.needs_review = False
    listing.moderation_notes = notes or ""
    listing.moderated_by = admin_user
    listing.moderated_at = timezone.now()
    listing.available_from = listing.available_from or timezone.now()
    _prepare_listing_fields(listing)
    listing.save(
        update_fields=[
            "status",
            "needs_review",
            "moderation_notes",
            "moderated_by",
            "moderated_at",
            "available_from",
            "postal_code",
            "slug",
            "updated_at",
        ]
    )

    record_listing_history(
        listing=listing,
        user=admin_user,
        event=Listing.ChangeEvent.APPROVED,
        details="Approved by moderation",
    )
    return listing


@transaction.atomic
def moderate_reject(*, listing: Listing, admin_user, notes: str) -> Listing:
    listing.status = Listing.Status.REJECTED
    listing.needs_review = False
    listing.moderation_notes = notes or ""
    listing.moderated_by = admin_user
    listing.moderated_at = timezone.now()
    listing.save(
        update_fields=[
            "status",
            "needs_review",
            "moderation_notes",
            "moderated_by",
            "moderated_at",
            "updated_at",
        ]
    )

    record_listing_history(
        listing=listing,
        user=admin_user,
        event=Listing.ChangeEvent.REJECTED,
        details=notes or "Rejected",
    )
    return listing


@transaction.atomic
def mark_sold(*, listing: Listing, user) -> Listing:
    listing.status = Listing.Status.SOLD
    listing.save(update_fields=["status", "updated_at"])
    record_listing_history(
        listing=listing,
        user=user,
        event=Listing.ChangeEvent.STATUS_UPDATED,
        details="Marked as SOLD",
    )
    return listing


@transaction.atomic
def archive_listing(*, listing: Listing, user) -> Listing:
    listing.status = Listing.Status.ARCHIVED
    listing.save(update_fields=["status", "updated_at"])
    record_listing_history(
        listing=listing,
        user=user,
        event=Listing.ChangeEvent.STATUS_UPDATED,
        details="Archived",
    )
    return listing


@transaction.atomic
def reactivate_listing(*, listing: Listing, user) -> Listing:
    listing.status = Listing.Status.PUBLISHED
    listing.needs_review = False
    _prepare_listing_fields(listing)
    listing.save(
        update_fields=[
            "status",
            "needs_review",
            "postal_code",
            "slug",
            "updated_at",
        ]
    )
    record_listing_history(
        listing=listing,
        user=user,
        event=Listing.ChangeEvent.STATUS_UPDATED,
        details="Listing reactivated",
    )
    return listing


def _prepare_listing_fields(listing: Listing) -> None:
    # sync postal_code from city
    if listing.location_city:
        listing.postal_code = listing.location_city.postal_code

    # slug
    if listing.title:
        listing.slug = (listing.slug or slugify(listing.title))[:160]


def record_listing_history(*, listing: Listing, user, event: str, details: str) -> None:
    actor_role = (
        ListingChangeLog.ActorRole.ADMIN
        if user and getattr(user, "is_staff", False)
        else ListingChangeLog.ActorRole.SELLER
    )
    ListingChangeLog.objects.create(
        listing=listing,
        user=user if user and getattr(user, "is_authenticated", False) else None,
        actor_role=actor_role,
        event=event,
        details=details,
    )
