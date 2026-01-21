# listings/services/favorite.py
from django.db import transaction

from listings.models import Favorite, Listing


@transaction.atomic
def toggle_favorite(*, listing: Listing, user) -> bool:
    favorite, created = Favorite.objects.get_or_create(user=user, listing=listing)
    if not created:
        favorite.delete()
    return created
