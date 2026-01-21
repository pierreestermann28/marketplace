from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import Category
from location.models import City

from listings.models import Favorite, Listing
from listings.queries import (
    build_home_feed_queryset,
    build_listing_detail_queryset,
    get_my_listings_queryset,
)


class ListingQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            email="user@example.com", password="password123"
        )
        cls.category = Category.objects.create(name="Furniture", slug="furniture")
        cls.city = City.objects.create(name="Lyon", postal_code="69000", slug="lyon-69000")
        cls.published = Listing.objects.create(
            seller=cls.user,
            title="Published item",
            status=Listing.Status.PUBLISHED,
            category=cls.category,
            location_city=cls.city,
            currency="EUR",
        )
        cls.reserved = Listing.objects.create(
            seller=cls.user,
            title="Reserved item",
            status=Listing.Status.RESERVED,
            currency="EUR",
        )
        cls.archived = Listing.objects.create(
            seller=cls.user,
            title="Archived item",
            status=Listing.Status.ARCHIVED,
            currency="EUR",
        )

    def test_build_home_feed_queryset_respects_status_and_city(self):
        filters = {"city_ids": [str(self.city.id)]}
        queryset = build_home_feed_queryset(
            filters, self.user, status_filter=[Listing.Status.PUBLISHED, Listing.Status.RESERVED]
        )
        self.assertIn(self.published, queryset)
        self.assertNotIn(self.archived, queryset)

    def test_build_listing_detail_queryset_handles_favorites(self):
        Favorite.objects.create(user=self.user, listing=self.published)
        queryset = build_listing_detail_queryset(self.user)
        self.assertIn(self.published, queryset)
        listing = queryset.get(id=self.published.id)
        self.assertTrue(getattr(listing, "is_favorited"))

    def test_get_my_listings_queryset_returns_seller_listings(self):
        queryset = get_my_listings_queryset(user=self.user)
        self.assertIn(self.published, queryset)
        self.assertIn(self.reserved, queryset)
