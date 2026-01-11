import shutil
import tempfile
from decimal import Decimal

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
