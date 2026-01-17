import shutil
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from mediahub.models import BatchUpload, ImageAsset, MediaAsset

from .models import DetectedItem
from .services.publishing import publish_detected_item


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\xda"
    b"c\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xe1\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_image_file(name="test.png"):
    return SimpleUploadedFile(name, PNG_BYTES, content_type="image/png")


class IngestionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="seller@example.com", password="pass12345")
        self.staff = User.objects.create_user(
            email="moderator@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.batch = BatchUpload.objects.create(owner=self.user, media_count=1)
        image_asset = ImageAsset.objects.create(user=self.user, image=make_image_file())
        self.media_asset = MediaAsset.objects.create(batch=self.batch, image_asset=image_asset)
        self.detected_item = DetectedItem.objects.create(
            owner=self.user,
            batch=self.batch,
            hero_asset=self.media_asset,
            title_suggested="Table vintage",
            price_low=Decimal("45.00"),
        )

    def test_publish_detected_item_creates_listing_with_image(self):
        listing = publish_detected_item(self.detected_item)
        self.assertEqual(listing.seller, self.user)
        self.assertEqual(listing.title, self.detected_item.title_suggested)
        self.assertTrue(listing.images.exists())
        primary = listing.images.first()
        self.assertEqual(primary.image_asset, self.media_asset.image_asset)
        self.assertEqual(listing.source_item, self.detected_item)

    def test_user_can_approve_swipe_sets_status(self):
        self.client.force_login(self.user)
        url = reverse("ingestion:detecteditem_approve", kwargs={"item_id": self.detected_item.id})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.detected_item.refresh_from_db()
        self.assertEqual(self.detected_item.status, DetectedItem.Status.USER_APPROVED)

    def test_user_can_reject_swipe_sets_status(self):
        self.client.force_login(self.user)
        url = reverse("ingestion:detecteditem_reject", kwargs={"item_id": self.detected_item.id})
        self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.detected_item.refresh_from_db()
        self.assertEqual(self.detected_item.status, DetectedItem.Status.USER_REJECTED)

    def test_admin_approval_creates_listing_and_marks_status(self):
        self.detected_item.status = DetectedItem.Status.USER_APPROVED
        self.detected_item.save(update_fields=["status"])
        self.client.force_login(self.staff)
        url = reverse("ingestion:detecteditem_admin_approve", kwargs={"item_id": self.detected_item.id})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.detected_item.refresh_from_db()
        self.assertEqual(self.detected_item.status, DetectedItem.Status.ADMIN_APPROVED)
        self.assertIsNotNone(self.detected_item.listing)

    def test_admin_rejection_marks_status(self):
        self.detected_item.status = DetectedItem.Status.USER_APPROVED
        self.detected_item.save(update_fields=["status"])
        self.client.force_login(self.staff)
        url = reverse("ingestion:detecteditem_admin_reject", kwargs={"item_id": self.detected_item.id})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.detected_item.refresh_from_db()
        self.assertEqual(self.detected_item.status, DetectedItem.Status.ADMIN_REJECTED)

    @patch("ingestion.views.analyze_batch")
    def test_batch_retry_clears_items_and_requeues(self, mock_analyze):
        self.batch.status = BatchUpload.Status.FAILED
        self.batch.error_message = "boom"
        self.batch.save(update_fields=["status", "error_message"])
        self.client.force_login(self.user)
        url = reverse("ingestion:batch_processing_retry", kwargs={"batch_id": self.batch.id})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, BatchUpload.Status.PENDING)
        self.assertEqual(self.batch.error_message, "")
        self.assertEqual(self.batch.detected_items.count(), 0)
        mock_analyze.delay.assert_called_once_with(str(self.batch.id))

    @patch("ingestion.tasks._compute_file_hash", return_value="cached-hash")
    def test_duplicate_hash_reuses_cached_result(self, mock_hash):
        self.media_asset.file_hash = "cached-hash"
        self.media_asset.save(update_fields=["file_hash"])
        self.detected_item.title_suggested = "Détec cache"
        self.detected_item.description_suggested = "Détection déjà connue"
        self.detected_item.metadata_json = {"cached": True}
        self.detected_item.save(
            update_fields=["title_suggested", "description_suggested", "metadata_json"]
        )
        new_batch = BatchUpload.objects.create(owner=self.user, media_count=1)
        image_asset = ImageAsset.objects.create(user=self.user, image=make_image_file("copy.png"))
        new_asset = MediaAsset.objects.create(batch=new_batch, image_asset=image_asset)
        analyze_batch.__wrapped__(None, str(new_batch.id))
        cached_item = DetectedItem.objects.filter(hero_asset=new_asset).first()
        self.assertIsNotNone(cached_item)
        self.assertTrue(cached_item.is_cached_result)
        self.assertEqual(cached_item.title_suggested, self.detected_item.title_suggested)
        self.assertEqual(cached_item.metadata_json.get("cached"), True)

    @override_settings(FREE_DETECTED_ITEM_QUOTA_PER_MONTH=1)
    def test_quota_limits_new_detections(self):
        self.client.force_login(self.user)
        analyze_batch.__wrapped__(None, str(self.batch.id))
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, BatchUpload.Status.FAILED)
        self.assertIn("Quota mensuel d’IA atteint", self.batch.error_message)

    @override_settings(FREE_LISTING_QUOTA_PER_MONTH=0)
    def test_admin_can_override_quota_limits(self):
        self.detected_item.status = DetectedItem.Status.USER_APPROVED
        self.detected_item.save(update_fields=["status"])
        self.client.force_login(self.staff)
        url = reverse("ingestion:detecteditem_admin_approve", kwargs={"item_id": self.detected_item.id})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.detected_item.refresh_from_db()
        self.assertEqual(self.detected_item.status, DetectedItem.Status.ADMIN_APPROVED)
        self.assertIsNotNone(self.detected_item.listing)
