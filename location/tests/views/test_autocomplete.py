from django.test import TestCase
from django.urls import reverse

from location.models import City


class CityAutocompleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        City.objects.create(
            name="Paris",
            postal_code="75001",
            slug="paris-75001",
            department_code="75",
            department_name="Paris",
            region_code="11",
            region_name="Île-de-France",
        )
        City.objects.create(
            name="Lyon",
            postal_code="69001",
            slug="lyon-69001",
            department_code="69",
            department_name="Rhône",
            region_code="84",
            region_name="Auvergne-Rhône-Alpes",
        )

    def test_returns_matches_for_name_query(self):
        response = self.client.get(reverse("location:city-autocomplete"), {"q": "Par"})
        self.assertEqual(response.status_code, 200)
        results = response.json().get("results") or []
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Paris")

    def test_filters_by_postal_code_prefix(self):
        response = self.client.get(reverse("location:city-autocomplete"), {"postal_code": "69"})
        results = response.json().get("results") or []
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Lyon")

    def test_returns_empty_when_no_query_provided(self):
        response = self.client.get(reverse("location:city-autocomplete"))
        self.assertFalse(response.json().get("results"))
