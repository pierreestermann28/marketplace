from django.db.models.signals import post_save
from django.dispatch import receiver

from .alerts import maybe_alert_high_pending
from .models import DetectedItem


@receiver(post_save, sender=DetectedItem)
def monitor_pending_counts(sender, **kwargs):
    maybe_alert_high_pending()
