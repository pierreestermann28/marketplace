# accounts/services/subscriptions.py
from __future__ import annotations

import stripe

from billing.services import get_user_entitlement
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from typing import Dict, Optional


UserModel = get_user_model()


class StripeConfigurationError(Exception):
    pass


def _build_absolute_url(request, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return request.build_absolute_uri(path)


def _ensure_api_key():
    stripe.api_key = settings.STRIPE_SECRET_KEY or ""


def _retrieve_subscription(subscription_id: Optional[str]) -> Dict:
    if not subscription_id:
        return {}
    try:
        _ensure_api_key()
        return stripe.Subscription.retrieve(subscription_id)
    except stripe.error.StripeError:
        return {}


def create_checkout_session(*, user, request) -> stripe.checkout.Session:
    price_id = settings.STRIPE_PREMIUM_PRICE_ID
    secret = settings.STRIPE_SECRET_KEY
    if not price_id or not secret:
        raise StripeConfigurationError("Stripe non configuré")
    stripe.api_key = secret
    return stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=user.email,
        allow_promotion_codes=True,
        subscription_data={"metadata": {"user_id": str(user.pk)}},
        metadata={"user_id": str(user.pk)},
        success_url=_build_absolute_url(
            request, settings.STRIPE_CHECKOUT_SUCCESS_URL
        ),
        cancel_url=_build_absolute_url(
            request, settings.STRIPE_CHECKOUT_CANCEL_URL
        ),
    )


def parse_stripe_event(request) -> Dict:
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        raise StripeConfigurationError("Stripe webhook non configuré")
    _ensure_api_key()
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    return stripe.Webhook.construct_event(payload, sig_header, secret)


def get_user_from_metadata(metadata: Dict, email: Optional[str] = None):
    user_id = metadata.get("user_id")
    if user_id:
        try:
            return UserModel.objects.get(pk=int(user_id))
        except (ValueError, UserModel.DoesNotExist):
            return None
    if email:
        return UserModel.objects.filter(email=email).first()
    return None


def apply_premium_entitlement(user, subscription_payload: Optional[Dict] = None):
    entitlement = get_user_entitlement(user)
    if not entitlement:
        return
    entitlement.is_premium = True
    premium_until = None
    if subscription_payload:
        period_end = subscription_payload.get("current_period_end")
        if period_end:
            try:
                timestamp = int(period_end)
            except (TypeError, ValueError):
                timestamp = None
            if timestamp:
                premium_until = timezone.datetime.fromtimestamp(
                    timestamp, tz=timezone.utc
                )
    entitlement.premium_until = premium_until
    entitlement.save(update_fields=["is_premium", "premium_until"])


def revoke_premium_entitlement(user):
    entitlement = get_user_entitlement(user)
    if not entitlement:
        return
    entitlement.is_premium = False
    entitlement.premium_until = None
    entitlement.save(update_fields=["is_premium", "premium_until"])


def handle_stripe_event(event) -> Optional[UserModel]:
    _ensure_api_key()
    data = event.get("data", {}).get("object", {}) or {}
    metadata = data.get("metadata", {})
    user = get_user_from_metadata(metadata, email=data.get("customer_email"))
    if not user:
        return None
    event_type = event.get("type")
    if event_type == "checkout.session.completed":
        subscription_id = data.get("subscription")
        subscription_payload = _retrieve_subscription(subscription_id)
        apply_premium_entitlement(user, subscription_payload)
    elif event_type in {
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        status = data.get("status")
        if status in {"active", "trialing"}:
            apply_premium_entitlement(user, data)
        else:
            revoke_premium_entitlement(user)
    return user


__all__ = [
    "StripeConfigurationError",
    "create_checkout_session",
    "handle_stripe_event",
    "parse_stripe_event",
    "apply_premium_entitlement",
    "revoke_premium_entitlement",
    "get_user_from_metadata",
]
