# listings/services/alerts.py
from django.db import IntegrityError, transaction

from listings.models import SearchAlert, SearchAlertNotification, Listing


def alert_matches_listing(*, alert: SearchAlert, listing: Listing) -> bool:
    if listing.seller_id == alert.user_id:
        return False

    if alert.keyword:
        text = f"{listing.title} {listing.description}".lower()
        if alert.keyword.lower() not in text:
            return False

    if alert.location_city_id and listing.location_city_id != alert.location_city_id:
        return False

    if alert.category_id and listing.category_id != alert.category_id:
        return False

    return True


@transaction.atomic
def notify_alert_for_listing(*, alert: SearchAlert, listing: Listing) -> bool:
    """
    Crée SearchAlertNotification si pas déjà créé.
    Retourne True si notification créée.
    """
    try:
        SearchAlertNotification.objects.create(alert=alert, listing=listing)
        return True
    except IntegrityError:
        return False
