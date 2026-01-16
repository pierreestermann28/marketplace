from django.conf import settings
from django.core.cache import cache
from django.core.mail import mail_admins
from django.urls import reverse
from django.utils import timezone

from .models import DetectedItem


PENDING_ALERT_THRESHOLD = getattr(settings, "INGESTION_PENDING_ALERT_THRESHOLD", 120)
PENDING_ALERT_COOLDOWN = getattr(
    settings, "INGESTION_PENDING_ALERT_COOLDOWN_SEC", 60 * 30
)
PENDING_ALERT_CACHE_KEY = "ingestion_pending_alert_last_sent"


def maybe_alert_high_pending():
    pending = DetectedItem.objects.filter(status=DetectedItem.Status.PENDING).count()
    if pending < PENDING_ALERT_THRESHOLD:
        cache.delete(PENDING_ALERT_CACHE_KEY)
        return

    last_sent = cache.get(PENDING_ALERT_CACHE_KEY)
    if last_sent:
        return

    if not settings.ADMINS:
        return

    subject = "[StillUseful] Lots en attente importants"
    base_url = getattr(settings, "SITE_URL", "").rstrip("/")
    admin_url = f"{base_url}{reverse('ingestion:admin_swipe')}"
    message = "\n".join(
        [
            "Le flux de modération contient plus de lots en attente que la moyenne.",
            f"Lots détectés en attente : {pending}",
            f"Seuil actuel : {PENDING_ALERT_THRESHOLD}",
            f"Dashboard modération : {admin_url or 'non configuré'}",
            f"Horodatage : {timezone.now().isoformat()}",
        ]
    )
    mail_admins(subject, message)
    cache.set(PENDING_ALERT_CACHE_KEY, timezone.now().isoformat(), PENDING_ALERT_COOLDOWN)
