import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Category

from .models import Favorite, Listing


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\xda"
    b"c\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xe1\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_image_file(name="test.png"):
    return SimpleUploadedFile(name, PNG_BYTES, content_type="image/png")


def get_listings_from_response(response):
    listings = response.context["listings"]
    return list(getattr(listings, "object_list", listings))


class FavoriteToggleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.seller = User.objects.create_user(username="seller", password="password123")
        cls.buyer = User.objects.create_user(username="buyer", password="password123")
        cls.listing = Listing.objects.create(
            seller=cls.seller,
            title="Vintage chair",
        )

    def test_toggle_creates_favorite(self):
        self.client.force_login(self.buyer)
        url = reverse("listing_favorite", kwargs={"listing_id": self.listing.id})

        response = self.client.post(url, data={"next": "/"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Favorite.objects.filter(user=self.buyer, listing=self.listing).count(), 1)

    def test_toggle_removes_favorite(self):
        Favorite.objects.create(user=self.buyer, listing=self.listing)
        self.client.force_login(self.buyer)
        url = reverse("listing_favorite", kwargs={"listing_id": self.listing.id})

        response = self.client.post(url, data={"next": "/"})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Favorite.objects.filter(user=self.buyer, listing=self.listing).exists())

    def test_requires_login(self):
        url = reverse("listing_favorite", kwargs={"listing_id": self.listing.id})

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/auth/login/"))


class ListingViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.seller = User.objects.create_user(username="seller", password="password123")
        cls.other_user = User.objects.create_user(username="other", password="password123")
        cls.category = Category.objects.create(name="Furniture", slug="furniture")
        cls.category_other = Category.objects.create(name="Decor", slug="decor")
        cls.listing_main = Listing.objects.create(
            seller=cls.seller,
            title="Vintage chair",
            city="Paris",
            status=Listing.Status.PUBLISHED,
            category=cls.category,
            currency="EUR",
        )
        cls.listing_other = Listing.objects.create(
            seller=cls.seller,
            title="Modern lamp",
            city="Lyon",
            status=Listing.Status.PUBLISHED,
            category=cls.category_other,
            currency="EUR",
        )
        cls.listing_draft = Listing.objects.create(
            seller=cls.seller,
            title="Hidden draft",
            status=Listing.Status.DRAFT,
            currency="EUR",
        )

    def test_home_feed_filters(self):
        url = reverse("home")
        response = self.client.get(
            url,
            {"q": "Vintage", "city": "Paris", "category": self.category.slug},
        )

        self.assertEqual(response.status_code, 200)
        listings = get_listings_from_response(response)
        self.assertEqual(listings, [self.listing_main])

    def test_home_feed_excludes_unpublished(self):
        response = self.client.get(reverse("home"))

        listings = get_listings_from_response(response)
        self.assertIn(self.listing_main, listings)
        self.assertIn(self.listing_other, listings)
        self.assertNotIn(self.listing_draft, listings)

    def test_listing_detail_requires_matching_slug(self):
        url = reverse(
            "listing_detail",
            kwargs={"slug": "wrong-slug", "uuid": self.listing_main.id},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_my_listings_requires_login(self):
        response = self.client.get(reverse("my_listings"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/auth/login/"))

    def test_my_listings_shows_only_seller_listings(self):
        Listing.objects.create(
            seller=self.other_user,
            title="Other listing",
            status=Listing.Status.PUBLISHED,
            currency="EUR",
        )
        self.client.force_login(self.seller)

        response = self.client.get(reverse("my_listings"))

        self.assertEqual(response.status_code, 200)
        listings = list(response.context["listings"])
        self.assertIn(self.listing_main, listings)
        self.assertIn(self.listing_other, listings)
        self.assertIn(self.listing_draft, listings)
        self.assertEqual(len(listings), 3)


class ListingWorkflowTests(TestCase):
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

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.seller = User.objects.create_user(username="seller", password="password123")
        cls.category = Category.objects.create(name="Furniture", slug="furniture")

    def test_listing_start_creates_listing_and_images(self):
        self.client.force_login(self.seller)
        url = reverse("listing_create")

        response = self.client.post(
            url,
            data={"images": [make_image_file("one.png"), make_image_file("two.png")]},
        )

        self.assertEqual(response.status_code, 302)
        listing = Listing.objects.get(seller=self.seller)
        self.assertEqual(listing.status, Listing.Status.DRAFT)
        self.assertEqual(listing.images.count(), 2)
        self.assertEqual(response["Location"], reverse("listing_submit", kwargs={"pk": listing.id}))

    def test_photo_upload_adds_images(self):
        listing = Listing.objects.create(
            seller=self.seller,
            title="Upload target",
            status=Listing.Status.DRAFT,
            currency="EUR",
        )
        self.client.force_login(self.seller)
        url = reverse("listing_photos", kwargs={"pk": listing.id})

        response = self.client.post(
            url,
            data={"images": [make_image_file("three.png")]},
        )

        self.assertEqual(response.status_code, 302)
        listing.refresh_from_db()
        self.assertEqual(listing.images.count(), 1)
        self.assertEqual(response["Location"], reverse("listing_submit", kwargs={"pk": listing.id}))

    def test_submit_for_review_sets_status(self):
        listing = Listing.objects.create(
            seller=self.seller,
            title="Draft listing",
            status=Listing.Status.DRAFT,
            currency="EUR",
        )
        self.client.force_login(self.seller)
        url = reverse("listing_submit", kwargs={"pk": listing.id})

        response = self.client.post(
            url,
            data={
                "title": "Draft listing",
                "category": self.category.id,
                "description": "Simple description",
                "condition": Listing.Condition.GOOD,
                "price_cents": 2500,
                "currency": "EUR",
                "postal_code": "75001",
                "city": "Paris",
            },
        )

        listing.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("my_listings"))
        self.assertEqual(listing.status, Listing.Status.PENDING_REVIEW)

    def test_review_queue_updates_status(self):
        staff = get_user_model().objects.create_user(
            username="staff",
            password="password123",
            is_staff=True,
        )
        listing = Listing.objects.create(
            seller=self.seller,
            title="Needs review",
            status=Listing.Status.PENDING_REVIEW,
            currency="EUR",
        )
        self.client.force_login(staff)
        url = reverse("review_queue")

        response = self.client.post(url, data={"listing_id": listing.id, "action": "approve"})

        listing.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(listing.status, Listing.Status.PUBLISHED)
        self.assertEqual(listing.moderated_by, staff)
        self.assertIsNotNone(listing.moderated_at)

    def test_review_queue_denies_non_staff(self):
        listing = Listing.objects.create(
            seller=self.seller,
            title="Needs review",
            status=Listing.Status.PENDING_REVIEW,
            currency="EUR",
        )
        self.client.force_login(self.seller)
        url = reverse("review_queue")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
