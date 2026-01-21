from django.contrib.auth import get_user_model
from django.test import TestCase

from listings.models import Listing
from reports.models import Report
from reports.services import AlreadyReportedError, create_report


class CreateReportServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.listing = Listing.objects.create(
            seller=self.user,
            title="Reportable item",
            status=Listing.Status.PUBLISHED,
        )

    def test_create_report_creates_record(self):
        report = create_report(
            reporter=self.user,
            target=self.listing,
            reason=Report.Reason.SPAM,
            details="details",
        )
        self.assertIsInstance(report, Report)
        self.assertEqual(report.target_object_id, str(self.listing.pk))

    def test_duplicate_report_raises(self):
        create_report(
            reporter=self.user,
            target=self.listing,
            reason=Report.Reason.SCAM,
            details="first",
        )
        with self.assertRaises(AlreadyReportedError):
            create_report(
                reporter=self.user,
                target=self.listing,
                reason=Report.Reason.SCAM,
                details="second",
            )
