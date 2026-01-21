from django.contrib.auth import get_user_model
from django.test import TestCase

from listings.models import Listing
from reports.queries import get_unresolved_reports
from reports.services import create_report, resolve_report


class AdminQueriesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.seller = User.objects.create_user(
            email="seller@example.com", password="pass"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", password="pass"
        )
        self.listing = Listing.objects.create(
            seller=self.seller,
            title="Reportable listing",
            status=Listing.Status.PUBLISHED,
        )

    def test_get_unresolved_reports_filters_resolved(self):
        create_report(
            reporter=self.user,
            target=self.listing,
            reason="spam",
        )
        resolved_report = create_report(
            reporter=self.other_user,
            target=self.listing,
            reason="scam",
        )
        resolve_report(report=resolved_report, by_user=self.seller)

        reports = get_unresolved_reports()
        self.assertEqual(reports.count(), 1)

    def test_get_unresolved_reports_respects_limit(self):
        create_report(
            reporter=self.user,
            target=self.listing,
            reason="spam",
        )
        create_report(
            reporter=self.seller,
            target=self.listing,
            reason="illegal",
        )
        reports = get_unresolved_reports(limit=1)
        self.assertEqual(len(reports), 1)
