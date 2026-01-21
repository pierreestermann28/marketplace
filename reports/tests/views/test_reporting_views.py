from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing
from messaging.models import Conversation
from reports.models import Report


class ReportingViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.seller = User.objects.create_user(email="seller@example.com", password="pass")
        self.listing = Listing.objects.create(
            seller=self.seller,
            title="Signalable item",
            status=Listing.Status.PUBLISHED,
        )
        self.conversation = Conversation.objects.create(
            listing=self.listing, buyer=self.user, seller=self.seller
        )

    def test_listing_report_creates_record(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse(
                "reports:listing_report",
                kwargs={"listing_id": self.listing.id},
            ),
            data={"reason": Report.Reason.SPAM, "details": "Test"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Report.objects.filter(
                reporter=self.user,
                target_content_type__model="listing",
                target_object_id=str(self.listing.pk),
            ).exists()
        )

    def test_conversation_report_creates_record(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("reports:conversation_report", kwargs={"pk": self.conversation.pk}),
            data={"reason": Report.Reason.SCAM},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Report.objects.filter(
                reporter=self.user,
                target_content_type__model="conversation",
                target_object_id=str(self.conversation.pk),
            ).exists()
        )
