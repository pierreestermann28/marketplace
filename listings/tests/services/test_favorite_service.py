from django.contrib.auth import get_user_model
from django.test import TestCase

from listings.models import Favorite, Listing
from listings.services.favorite import toggle_favorite


class FavoriteServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com", password="password123"
        )
        self.listing = Listing.objects.create(
            seller=self.user,
            title="Favorite service item",
        )

    def test_toggle_favorite_creates_and_removes(self):
        created = toggle_favorite(listing=self.listing, user=self.user)
        self.assertTrue(created)
        self.assertTrue(
            Favorite.objects.filter(user=self.user, listing=self.listing).exists()
        )

        created_again = toggle_favorite(listing=self.listing, user=self.user)
        self.assertFalse(created_again)
        self.assertFalse(
            Favorite.objects.filter(user=self.user, listing=self.listing).exists()
        )
