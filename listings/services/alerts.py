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


class SearchAlertError(Exception):
    pass


class SearchAlertAlreadyExists(SearchAlertError):
    pass


class SearchAlertNotFound(SearchAlertError):
    pass


def _build_search_alert_defaults():
    return {"is_active": True}


@transaction.atomic
def create_search_alert(
    *,
    user,
    keyword: str,
    location_city=None,
    category=None,
) -> SearchAlert:
    try:
        return SearchAlert.objects.create(
            user=user,
            keyword=keyword,
            location_city=location_city,
            category=category,
            **_build_search_alert_defaults(),
        )
    except IntegrityError:
        raise SearchAlertAlreadyExists()


@transaction.atomic
def delete_search_alert(*, alert_id, user) -> None:
    deleted, _ = SearchAlert.objects.filter(pk=alert_id, user=user).delete()
    if not deleted:
        raise SearchAlertNotFound()
