from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.entitlements import can_generate_detected_items, can_publish_listing
from accounts.models import UserEntitlement
from mediahub.models import BatchUpload
from listings.models import Listing
from ingestion.models import DetectedItem
from django.contrib.auth import get_user_model


class EntitlementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="user@example.com", password="pass")

    @override_settings(FREE_LISTING_QUOTA_PER_MONTH=1)
    def test_can_publish_listing_respects_quota(self):
        Listing.objects.create(seller=self.user, status=Listing.Status.PUBLISHED, title="Test")
        self.assertFalse(can_publish_listing(self.user))

    def test_premium_user_can_publish_unlimited(self):
        entitlement = UserEntitlement.objects.get(user=self.user)
        entitlement.is_premium = True
        entitlement.premium_until = timezone.now() + timedelta(days=30)
        entitlement.save()
        for _ in range(5):
            Listing.objects.create(seller=self.user, status=Listing.Status.PUBLISHED, title="Test")
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
