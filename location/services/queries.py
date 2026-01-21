# location/services/queries.py
from django.db.models import Q

from location.models import City


DEFAULT_LIMIT = 25
MAX_LIMIT = 100


def _normalize_limit(limit: int | str | None) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = DEFAULT_LIMIT
    if value < 1:
        value = DEFAULT_LIMIT
    return min(value, MAX_LIMIT)


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
    limit = min(max(1, int(limit)), MAX_LIMIT) if isinstance(limit, int) else _normalize_limit(limit)
    qs = City.objects.all()

    if query:
        qs = qs.filter(name__istartswith=query.strip())

    if postal_code:
        qs = qs.filter(postal_code__startswith=postal_code.strip())

    return qs.order_by("name", "postal_code")[:limit]


def serialize_city(city: City) -> dict:
    return {
        "id": city.id,
        "name": city.name,
        "postal_code": city.postal_code,
        "slug": city.slug,
        "display_name": f"{city.name} ({city.postal_code})",
        "department": city.department_name,
        "region": city.region_name,
    }


def autocomplete_cities(
    *,
    query: str | None = None,
    postal_code: str | None = None,
    limit: int | str | None = None,
) -> list[dict]:
    max_limit = _normalize_limit(limit)
    qs = search_cities(query=query, postal_code=postal_code, limit=max_limit)
    return [serialize_city(city) for city in qs]


def get_city_by_slug(*, slug: str) -> City:
    return City.objects.get(slug=slug)


def get_city_by_name_postal(*, name: str, postal_code: str) -> City:
    return City.objects.get(name=name, postal_code=postal_code)
