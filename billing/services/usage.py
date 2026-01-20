# billing/services/usage.py
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from billing.models import UsageCounter, UserEntitlement, current_month_period


class BillingError(Exception):
    pass


class QuotaExceeded(BillingError):
    pass


@dataclass(frozen=True)
class UsageSnapshot:
    scope: str
    period: object
    used: int
    limit: int | None  # None = unlimited (premium)


def _get_entitlement(user) -> UserEntitlement:
    ent, _ = UserEntitlement.objects.get_or_create(user=user)
    return ent


def _quota_limit_for(ent: UserEntitlement, scope: str) -> int | None:
    # Premium => unlimited
    if ent.is_premium_active:
        return None

    if scope == UsageCounter.SCOPE_LISTING_PUBLICATION:
        return int(ent.free_listing_quota)

    if scope == UsageCounter.SCOPE_DETECTED_ITEM:
        return int(ent.free_detected_item_quota)

    # Unknown scope => treat as not allowed (or unlimited if you prefer)
    raise BillingError(f"Unknown scope: {scope}")


def get_usage(*, user, scope: str, period=None) -> UsageSnapshot:
    if period is None:
        period = current_month_period()

    ent = _get_entitlement(user)
    limit = _quota_limit_for(ent, scope)

    counter = (
        UsageCounter.objects.filter(user=user, scope=scope, period=period)
        .only("count")
        .first()
    )
    used = int(counter.count) if counter else 0

    return UsageSnapshot(scope=scope, period=period, used=used, limit=limit)


def can_consume(*, user, scope: str, amount: int = 1, period=None) -> bool:
    snap = get_usage(user=user, scope=scope, period=period)
    if amount <= 0:
        raise ValueError("amount must be > 0")
    if snap.limit is None:
        return True
    return (snap.used + amount) <= snap.limit


@transaction.atomic
def consume(
    *,
    user,
    scope: str,
    amount: int = 1,
    period=None,
    raise_if_exceeded: bool = True,
) -> int:
    """
    Atomically increments usage if allowed.
    Returns the new count.
    """
    if amount <= 0:
        raise ValueError("amount must be > 0")
    if period is None:
        period = current_month_period()

    ent = _get_entitlement(user)
    limit = _quota_limit_for(ent, scope)

    # Premium => just increment (or even skip tracking, but tracking is useful)
    obj, _ = UsageCounter.objects.get_or_create(
        user=user,
        scope=scope,
        period=period,
        defaults={"count": 0},
    )

    # Enforce quota for free users
    if limit is not None:
        # Lock the row to avoid race conditions on concurrent requests
        obj = UsageCounter.objects.select_for_update().get(pk=obj.pk)
        if obj.count + amount > limit:
            if raise_if_exceeded:
                raise QuotaExceeded(
                    f"Quota exceeded for scope={scope}: used={obj.count}, amount={amount}, limit={limit}"
                )
            return obj.count

    UsageCounter.objects.filter(pk=obj.pk).update(count=F("count") + amount)
    obj.refresh_from_db(fields=["count"])
    return int(obj.count)


@transaction.atomic
def set_premium(*, user, until=None) -> UserEntitlement:
    """
    Turn on premium. If 'until' is None, premium is unlimited-time (V1).
    """
    ent = _get_entitlement(user)
    ent.is_premium = True
    ent.premium_until = until
    ent.save(update_fields=["is_premium", "premium_until", "updated_at"])
    return ent


@transaction.atomic
def revoke_premium(*, user) -> UserEntitlement:
    ent = _get_entitlement(user)
    ent.is_premium = False
    ent.premium_until = None
    ent.save(update_fields=["is_premium", "premium_until", "updated_at"])
    return ent
