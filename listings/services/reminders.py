# listings/services/reminders.py
from datetime import timedelta
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
