# listings/queries/listing_feed.py
from __future__ import annotations

from typing import Iterable, List

from django.db.models import (
    BooleanField,
    Exists,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Value,
)

from catalog.services import resolve_category_slugs
from location.models import City as LocationCity

from listings.models import Favorite, Listing, ListingImage, ListingView


def _clean_category_slugs(slugs: Iterable[str]) -> List[str]:
    return [slug.strip() for slug in slugs if slug and slug.strip()]


def _normalize_city_ids(raw_ids: Iterable[str]) -> List[int]:
    ids: List[int] = []
    for value in raw_ids:
        if not value:
            continue
        try:
            ids.append(int(value))
        except ValueError:
            continue
    return ids


def image_prefetch_queryset() -> QuerySet[ListingImage]:
    return ListingImage.objects.select_related("image_asset").order_by(
        "-is_primary", "sort_order"
    )


def build_home_feed_queryset(
    filters: dict, user, status_filter: Iterable[str]
) -> QuerySet[Listing]:
    qs: QuerySet[Listing] = Listing.objects.filter(status__in=status_filter)
    q = (filters.get("q") or "").strip()
    city = (filters.get("city") or "").strip()
    city_slug = (filters.get("city_slug") or "").strip()
    postal_code = (filters.get("postal_code") or "").strip()
    category = (filters.get("category") or "").strip()
    city_ids = _normalize_city_ids(filters.get("city_ids", []))
    category_slugs = _clean_category_slugs(filters.get("category_slugs", []))

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if city_ids:
        qs = qs.filter(location_city_id__in=city_ids)
    elif city_slug:
        qs = qs.filter(location_city__slug=city_slug)
    elif city:
        qs = qs.filter(location_city__name__icontains=city)
    elif postal_code:
        qs = qs.filter(postal_code__istartswith=postal_code)
    if category_slugs:
        qs = qs.filter(category__slug__in=category_slugs)
    elif category:
        qs = qs.filter(category__slug=category)

    image_qs = image_prefetch_queryset()
    if user and getattr(user, "is_authenticated", False):
        qs = qs.annotate(
            is_favorited=Exists(
                Favorite.objects.filter(user=user, listing=OuterRef("pk"))
            )
        )
        qs = annotate_with_seen(qs, user)
    else:
        qs = qs.annotate(is_favorited=Value(False, output_field=BooleanField()))
        qs = qs.annotate(is_seen=Value(False, output_field=BooleanField()))

    return (
        qs.select_related("category", "seller")
        .prefetch_related(Prefetch("images", queryset=image_qs))
        .order_by("-created_at")
    )


def annotate_with_seen(qs: QuerySet[Listing], user) -> QuerySet[Listing]:
    if not user or not getattr(user, "is_authenticated", False):
        return qs
    seen_qs = ListingView.objects.filter(user=user, listing=OuterRef("pk"))
    return qs.annotate(is_seen=Exists(seen_qs))


def resolve_selected_cities(city_ids: List[int]) -> List[dict]:
    if not city_ids:
        return []
    unique_ids = list(dict.fromkeys(city_ids))
    cities = (
        LocationCity.objects.filter(id__in=unique_ids)
        .order_by("name")
        .values("id", "name", "postal_code", "slug")
    )
    return [
        {
            "id": city["id"],
            "name": city["name"],
            "slug": city["slug"],
            "postal_code": city["postal_code"] or "",
            "display_name": (
                f"{city['name']} ({city['postal_code']})"
                if city["postal_code"]
                else city["name"]
            ),
        }
        for city in cities
    ]


def resolve_selected_categories(category_slugs: Iterable[str]) -> List[dict]:
    cleaned = _clean_category_slugs(category_slugs)
    if not cleaned:
        return []
    categories = resolve_category_slugs(cleaned)
    return [{"name": category.name, "slug": category.slug} for category in categories]


def build_filters_from_params(params) -> dict:
    city_ids = _normalize_city_ids(params.getlist("city_ids"))
    category_slugs = _clean_category_slugs(params.getlist("category_slugs"))
    return {
        "q": params.get("q", ""),
        "city": params.get("city", ""),
        "city_slug": params.get("city_slug", ""),
        "postal_code": params.get("postal_code", ""),
        "category": params.get("category", ""),
        "city_ids": [str(cid) for cid in city_ids],
        "category_slugs": category_slugs,
    }


def get_selected_city_ids(params) -> List[int]:
    return _normalize_city_ids(params.getlist("city_ids"))


def get_selected_category_slugs(params) -> List[str]:
    return _clean_category_slugs(params.getlist("category_slugs"))
