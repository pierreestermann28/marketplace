from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from .models import Listing, SearchAlert, SearchAlertNotification


def dispatch_search_alerts(listing: Listing):
    if listing.status != Listing.Status.PUBLISHED:
        return
    alerts = SearchAlert.objects.filter(is_active=True).exclude(user=listing.seller)
    for alert in alerts:
        if not alert.matches(listing):
            continue
        notification, created = SearchAlertNotification.objects.get_or_create(
            alert=alert, listing=listing
        )
        if not created:
            continue
        if not alert.user.email:
            continue
        subject = f"Nouveau résultat pour votre recherche sur Swipe2Sell"
        base_url = getattr(settings, "SITE_URL", "").rstrip("/")
        listing_url = reverse("listing_detail", kwargs={"slug": listing.slug or "item", "uuid": listing.id})
        if base_url:
            listing_url = f"{base_url}{listing_url}"
        location_label = listing.city or listing.postal_code or listing.country_code or "Localisation inconnue"
        message = "\n".join(
            [
                f"Une annonce correspond à votre alerte : {alert}",
                f"Titre : {listing.title}",
                f"Prix : {listing.price_cents / 100 if listing.price_cents else 'À définir'} {listing.currency}",
                f"Lien : {listing_url}",
                f"Ville : {location_label}",
            ]
        )
        sender = getattr(settings, "DEFAULT_FROM_EMAIL", settings.SERVER_EMAIL)
        send_mail(subject, message, sender, [alert.user.email], fail_silently=True)
        alert.last_sent = timezone.now()
        alert.save(update_fields=["last_sent"])
