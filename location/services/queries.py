# location/services/queries.py
from django.db.models import Q

from location.models import City


DEFAULT_LIMIT = 25
MAX_LIMIT = 100


def search_cities(
    *,
    query: str | None = None,
    postal_code: str | None = None,
    limit: int = DEFAULT_LIMIT,
):
    """
    Recherche par nom (prefix) et/ou code postal.
    Utilisé pour autocomplete, formulaires, API publiques.
    """
    limit = min(max(1, int(limit)), MAX_LIMIT)

    qs = City.objects.all()

    if query:
        qs = qs.filter(name__istartswith=query.strip())

    if postal_code:
        qs = qs.filter(postal_code__startswith=postal_code.strip())

    return qs.order_by("name", "postal_code")[:limit]


def get_city_by_slug(*, slug: str) -> City:
    return City.objects.get(slug=slug)


def get_city_by_name_postal(*, name: str, postal_code: str) -> City:
    return City.objects.get(name=name, postal_code=postal_code)
