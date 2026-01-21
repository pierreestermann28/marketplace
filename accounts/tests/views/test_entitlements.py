from datetime import timedelta
import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

import stripe

from billing.entitlements import (
    can_generate_detected_items,
    can_publish_listing,
    ensure_listing_quota,
    record_listing_publication,
    QuotaExceeded,
)
from billing.models import UserEntitlement, UsageCounter
from ingestion.models import BatchUpload
from listings.models import Listing
from ingestion.models import DetectedItem
from django.contrib.auth import get_user_model


class EntitlementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="user@example.com", password="pass")

    def _stripe_signature(self, payload):
        secret = settings.STRIPE_WEBHOOK_SECRET
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{payload}".encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"), signed_payload, digestmod=hashlib.sha256
        ).hexdigest()
        return f"t={timestamp},v1={signature}"

    @override_settings(FREE_LISTING_QUOTA_PER_MONTH=1)
    def test_can_publish_listing_respects_quota(self):
        Listing.objects.create(
            seller=self.user, status=Listing.Status.PUBLISHED, title="Test"
        )
        self.assertFalse(can_publish_listing(self.user))

    def test_premium_user_can_publish_unlimited(self):
        entitlement = UserEntitlement.objects.get(user=self.user)
        entitlement.is_premium = True
        entitlement.premium_until = timezone.now() + timedelta(days=30)
        entitlement.save()
        for _ in range(5):
            Listing.objects.create(
                seller=self.user, status=Listing.Status.PUBLISHED, title="Test"
            )
        self.assertTrue(can_publish_listing(self.user))

    @override_settings(FREE_DETECTED_ITEM_QUOTA_PER_MONTH=1)
    def test_detected_item_quota_limits_free_users(self):
        batch = BatchUpload.objects.create(owner=self.user, media_count=0)
        DetectedItem.objects.create(owner=self.user, batch=batch)
        self.assertFalse(can_generate_detected_items(self.user))

    def test_premium_user_can_generate_detected_items(self):
        entitlement = UserEntitlement.objects.get(user=self.user)
        entitlement.is_premium = True
        entitlement.premium_until = timezone.now() + timedelta(days=30)
        entitlement.save()
        batch = BatchUpload.objects.create(owner=self.user, media_count=0)
        DetectedItem.objects.create(owner=self.user, batch=batch)
        self.assertTrue(can_generate_detected_items(self.user))

    def test_record_listing_publication_updates_usage(self):
        record_listing_publication(self.user)
        record_listing_publication(self.user, amount=2)
        counter = UsageCounter.objects.get(
            user=self.user,
            scope=UsageCounter.SCOPE_LISTING_PUBLICATION,
        )
        self.assertEqual(counter.count, 3)

    def test_ensure_listing_quota_raises(self):
        with override_settings(FREE_LISTING_QUOTA_PER_MONTH=0):
            with self.assertRaises(QuotaExceeded):
                ensure_listing_quota(self.user)

    @override_settings(
        STRIPE_WEBHOOK_SECRET="whsec_test",
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_PREMIUM_PRICE_ID="price_123",
    )
    @patch("accounts.services.subscriptions.stripe.Subscription.retrieve")
    def test_stripe_checkout_sets_premium(self, mock_subscription):
        mock_subscription.return_value = {
            "id": "sub_test",
            "current_period_end": int(
                (timezone.now() + timedelta(days=30)).timestamp()
            ),
            "status": "active",
            "metadata": {"user_id": str(self.user.pk)},
        }
        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"user_id": str(self.user.pk)},
                    "customer_email": self.user.email,
                    "subscription": "sub_test",
                }
            },
        }
        header = self._stripe_signature(json.dumps(payload))
        response = self.client.post(
            reverse("accounts:stripe_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header,
        )
        self.assertEqual(response.status_code, 200)
        entitlement = UserEntitlement.objects.get(user=self.user)
        self.assertTrue(entitlement.is_premium)
        self.assertIsNotNone(entitlement.premium_until)

    @override_settings(
        STRIPE_WEBHOOK_SECRET="whsec_test",
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_PREMIUM_PRICE_ID="price_123",
    )
    def test_stripe_subscription_deleted_revokes_premium(self):
        entitlement = UserEntitlement.objects.get(user=self.user)
        entitlement.is_premium = True
        entitlement.premium_until = timezone.now() + timedelta(days=30)
        entitlement.save()
        payload = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "metadata": {"user_id": str(self.user.pk)},
                    "status": "canceled",
                }
            },
        }
        header = self._stripe_signature(json.dumps(payload))
        response = self.client.post(
            reverse("accounts:stripe_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header,
        )
        self.assertEqual(response.status_code, 200)
        entitlement.refresh_from_db()
        self.assertFalse(entitlement.is_premium)
        self.assertIsNone(entitlement.premium_until)

    @override_settings(
        STRIPE_WEBHOOK_SECRET="whsec_test",
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_PREMIUM_PRICE_ID="price_123",
    )
    def test_stripe_webhook_fails_on_bad_signature(self):
        payload = {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {}, "customer_email": self.user.email}},
        }
        self.client.post(
            reverse("accounts:stripe_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad-signature",
        )
        entitlement = UserEntitlement.objects.get(user=self.user)
        self.assertFalse(entitlement.is_premium)
