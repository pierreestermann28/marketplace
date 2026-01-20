from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing


class AdminListingModerationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            email="seller@example.com", password="pass"
        )
        self.staff = User.objects.create_user(
            email="staff@example.com", password="pass", is_staff=True
        )
        self.published = Listing.objects.create(
            seller=self.seller,
            title="Published Item",
            status=Listing.Status.PUBLISHED,
        )
        self.archived = Listing.objects.create(
            seller=self.seller,
            title="Archived Item",
            status=Listing.Status.ARCHIVED,
        )

    def test_non_staff_cannot_access(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse("operations:admin_listings"))
        self.assertEqual(response.status_code, 403)

    def test_status_filter_limits_results(self):
        self.client.force_login(self.staff)
        url = (
            reverse("operations:admin_listings") + "?status=" + Listing.Status.PUBLISHED
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        listings = list(response.context["listings"])
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].id, self.published.id)

    def test_unpublish_action_sets_archived_and_notes(self):
        self.client.force_login(self.staff)
        note = "Contenu non conforme"
        response = self.client.post(
            reverse("operations:admin_listings"),
            data={"action": "unpublish", "listing_id": self.published.id, "note": note},
        )
        self.assertEqual(response.status_code, 302)
        self.published.refresh_from_db()
        self.assertEqual(self.published.status, Listing.Status.ARCHIVED)
        self.assertEqual(self.published.moderation_notes, note)
        self.assertEqual(self.published.moderated_by_id, self.staff.id)

    def test_ban_user_action_disables_seller(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("operations:admin_listings"),
            data={"action": "ban_user", "listing_id": self.archived.id},
        )
        self.assertEqual(response.status_code, 302)
        self.seller.refresh_from_db()
        self.assertFalse(self.seller.is_active)
