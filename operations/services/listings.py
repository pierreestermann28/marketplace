from __future__ import annotations

from typing import Tuple

from listings.models import Listing
from listings.services import (
    archive_listing,
    moderate_approve,
    moderate_reject,
)

from .users import ban_user


def handle_review_action(
    action: str, listing: Listing, admin_user, note: str = ""
) -> Tuple[str, bool]:
    if action == "approve":
        moderate_approve(listing=listing, admin_user=admin_user)
        return (
            f"L'annonce «{listing.title or listing.id}» est validée et repasse en ligne.",
            True,
        )
    if action == "reject":
        moderate_reject(listing=listing, admin_user=admin_user, notes=note)
        return (
            f"L'annonce «{listing.title or listing.id}» est refusée.",
            True,
        )
    return "Action inconnue.", False


def handle_admin_listing_action(
    action: str, listing: Listing, admin_user, note: str = ""
) -> Tuple[str, bool]:
    if action == "unpublish":
        archive_listing(listing=listing, user=admin_user)
        return (
            f"L'annonce «{listing.title or listing.id}» est hors ligne.",
            True,
        )
    if action == "ban_user":
        ban_user(listing.seller)
        return (
            f"L'utilisateur {listing.seller.get_full_name() or listing.seller.email} est désactivé.",
            True,
        )
    if action == "approve":
        moderate_approve(listing=listing, admin_user=admin_user)
        return (
            f"L'annonce «{listing.title or listing.id}» est validée et repasse en ligne.",
            True,
        )
    if action == "reject":
        moderate_reject(listing=listing, admin_user=admin_user, notes=note)
        return (
            f"L'annonce «{listing.title or listing.id}» est refusée.",
            True,
        )
    return "Action inconnue.", False
