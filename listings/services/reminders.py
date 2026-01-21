# listings/services/reminders.py
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from listings.models import ListingReminder


def compute_notify_at_for_reminder(*, reminder: ListingReminder):
    available = reminder.listing.available_from
    if available:
        return available - timedelta(hours=6)
    return timezone.now()


def ensure_reminder_notify_at(*, reminder: ListingReminder) -> ListingReminder:
    if not reminder.notify_at:
        reminder.notify_at = compute_notify_at_for_reminder(reminder=reminder)
        reminder.save(update_fields=["notify_at"])
    return reminder


@transaction.atomic
def register_listing_reminder(*, listing, user) -> bool:
    reminder, created = ListingReminder.objects.get_or_create(user=user, listing=listing)
    if created:
        ensure_reminder_notify_at(reminder=reminder)
        _notify_seller(listing=listing, requester=user)
    return created


def _notify_seller(listing, requester):
    if not listing.seller.email:
        return
    subject = f"Un acheteur veut être prévenu pour {listing.title or 'votre annonce'}"
    sender = getattr(settings, "DEFAULT_FROM_EMAIL", settings.SERVER_EMAIL)
    message = "\n".join(
        [
            f"{requester.get_full_name() or requester.email} souhaite être notifié.",
            f"Annonce : {listing.title}",
            f"ID : {listing.id}",
            f"Disponible à partir de : {listing.available_from or 'à confirmer'}",
        ]
    )
    send_mail(subject, message, sender, [listing.seller.email], fail_silently=True)
