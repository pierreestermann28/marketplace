from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from billing.models import UsageCounter, UserEntitlement, current_month_period
from ingestion.models import DetectedItem


def get_user_entitlement(user):
    if not user or not user.is_authenticated:
        return None
    entitlement, _ = UserEntitlement.objects.get_or_create(user=user)
    return entitlement


def is_premium(user):
    entitlement = get_user_entitlement(user)
    return bool(entitlement and entitlement.is_premium_active)


def get_free_listing_quota(user):
    entitlement = get_user_entitlement(user)
    if entitlement:
        return entitlement.free_listing_quota
    return getattr(settings, "FREE_LISTING_QUOTA_PER_MONTH", 3)


def get_free_detected_item_quota(user):
    entitlement = get_user_entitlement(user)
    if entitlement:
        return entitlement.free_detected_item_quota
    return getattr(settings, "FREE_DETECTED_ITEM_QUOTA_PER_MONTH", 5)


def _listing_usage_this_month(user):
    period = current_month_period()
    counter = UsageCounter.objects.filter(
        user=user,
        scope=UsageCounter.SCOPE_LISTING_PUBLICATION,
        period=period,
    ).first()
    return counter.count if counter else 0


def can_publish_listing(user):
    if not user or not user.is_authenticated:
        return False
    if is_premium(user):
        return True
    usage = _listing_usage_this_month(user)
    return usage < get_free_listing_quota(user)


class QuotaExceeded(Exception):
    """Raised when a quota has been exhausted."""


def ensure_listing_quota(user):
    if not can_publish_listing(user):
        raise QuotaExceeded("Quota mensuel de publications atteint. Passez à l’offre premium.")


def record_listing_publication(user, amount=1):
    if not user or not user.is_authenticated:
        return
    period = current_month_period()
    counter, _ = UsageCounter.objects.get_or_create(
        user=user,
        scope=UsageCounter.SCOPE_LISTING_PUBLICATION,
        period=period,
    )
    counter.increment(amount)


def detected_item_usage_window(user):
    window_days = getattr(settings, "DETECTED_ITEM_QUOTA_WINDOW_DAYS", 30)
    window_start = timezone.now() - timedelta(days=window_days)
    return DetectedItem.objects.filter(
        owner=user, is_cached_result=False, created_at__gte=window_start
    ).count()


def can_generate_detected_items(user):
    if not user or not user.is_authenticated:
        return False
    if is_premium(user):
        return True
    return detected_item_usage_window(user) < get_free_detected_item_quota(user)


def quota_remaining_detected_items(user):
    if is_premium(user):
        return None
    return max(
        get_free_detected_item_quota(user) - detected_item_usage_window(user), 0
    )
