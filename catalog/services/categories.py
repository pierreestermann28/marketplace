# catalog/services/categories.py
from typing import Iterable, List, Optional

from django.db.models import QuerySet
from django.utils.text import slugify

from catalog.models import Category


def list_categories(order_by: Iterable[str] | None = None) -> QuerySet:
    qs = Category.objects.all()
    if order_by:
        qs = qs.order_by(*order_by)
    return qs


def get_categories_by_slugs(slugs: Iterable[str]) -> QuerySet:
    slugs = [slug.strip() for slug in slugs if slug and slug.strip()]
    if not slugs:
        return Category.objects.none()
    return Category.objects.filter(slug__in=slugs).order_by("name")


def get_categories_with_listings(statuses: Iterable[str]) -> QuerySet:
    return (
        Category.objects.filter(listings__status__in=statuses)
        .distinct()
        .order_by("name")
    )


def resolve_category_slugs(slugs: Iterable[str]) -> List[Category]:
    return list(get_categories_by_slugs(slugs))


def find_category_by_slug_or_name(value: str) -> Optional[Category]:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    slug = slugify(normalized)
    if slug:
        category = Category.objects.filter(slug__iexact=slug).first()
        if category:
            return category
    return Category.objects.filter(name__iexact=normalized).first()
