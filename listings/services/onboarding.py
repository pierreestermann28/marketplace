# listings/services/onboarding.py
from django.db import transaction

from catalog.services import resolve_category_slugs

from listings.models import OnboardingProfile, SearchAlert


@transaction.atomic
def create_onboarding_alerts(*, user, category_slugs, location_city):
    if not category_slugs and not location_city:
        return
    categories = resolve_category_slugs(category_slugs) if category_slugs else []
    if categories:
        alerts = []
        for category in categories:
            alert, _ = SearchAlert.objects.get_or_create(
                user=user,
                keyword="",
                location_city=location_city,
                category=category,
                defaults={"is_active": True},
            )
            alerts.append(alert)
        return alerts
    alert, _ = SearchAlert.objects.get_or_create(
        user=user,
        keyword="",
        location_city=location_city,
        category=None,
        defaults={"is_active": True},
    )
    return [alert]


@transaction.atomic
def update_onboarding_profile(
    *, user, purpose, location_city, radius, category_slugs
):
    profile, _ = OnboardingProfile.objects.get_or_create(user=user)
    profile.purpose = purpose
    profile.location_city = location_city
    try:
        profile.radius_km = int(radius)
    except (TypeError, ValueError):
        profile.radius_km = None
    profile.save(update_fields=["purpose", "location_city", "radius_km", "updated_at"])
    categories = resolve_category_slugs(category_slugs)
    profile.categories.set(categories)
