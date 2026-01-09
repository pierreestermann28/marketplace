from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from listings.models import Listing

from .models import Conversation, Message


class MessagingViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.buyer = User.objects.create_user(email="buyer@example.com", password="password123")
        cls.seller = User.objects.create_user(email="seller@example.com", password="password123")
        cls.other = User.objects.create_user(email="other@example.com", password="password123")
        cls.listing = Listing.objects.create(
            seller=cls.seller,
            title="Test listing",
            price_cents=1234,
            currency="EUR",
        )
        cls.conversation = Conversation.objects.create(
            listing=cls.listing,
            buyer=cls.buyer,
            seller=cls.seller,
            last_message_at=timezone.now(),
        )
        cls.listing_no_convo = Listing.objects.create(
            seller=cls.seller,
            title="Second listing",
            price_cents=2000,
            currency="EUR",
        )

    def test_htmx_post_renders_new_message(self):
        self.client.force_login(self.buyer)
        url = reverse("messages:detail", kwargs={"pk": self.conversation.pk})
        previous_last_message = self.conversation.last_message_at

        response = self.client.post(
            url,
            data={"text": "Hello from buyer"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Message.objects.filter(conversation=self.conversation).count(), 1
        )
        self.assertContains(response, "Hello from buyer")

        self.conversation.refresh_from_db()
        self.assertNotEqual(self.conversation.last_message_at, previous_last_message)

    def test_htmx_post_invalid_message_keeps_form_errors(self):
        self.client.force_login(self.buyer)
        url = reverse("messages:detail", kwargs={"pk": self.conversation.pk})

        response = self.client.post(
            url,
            data={"text": "Email me at test@example.com"},
            HTTP_HX_REQUEST="true",
        )
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Message.objects.filter(conversation=self.conversation).count(), 0
        )
        self.assertIn("text", response.context["form"].errors)

    def test_detail_denies_non_participant(self):
        self.client.force_login(self.other)
        url = reverse("messages:detail", kwargs={"pk": self.conversation.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_start_conversation_creates_and_redirects(self):
        self.client.force_login(self.buyer)
        url = reverse("messages:start", kwargs={"listing_id": self.listing_no_convo.id})

        response = self.client.get(url)

        conversation = Conversation.objects.get(
            listing=self.listing_no_convo,
            buyer=self.buyer,
        )
        expected_url = f"{reverse('messages:list')}?conversation={conversation.pk}"
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], expected_url)

    def test_start_conversation_blocks_self_contact(self):
        self.client.force_login(self.seller)
        url = reverse("messages:start", kwargs={"listing_id": self.listing_no_convo.id})

        response = self.client.get(url)

        expected_url = reverse(
            "listing_detail",
            kwargs={
                "slug": self.listing_no_convo.slug,
                "uuid": self.listing_no_convo.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], expected_url)
        self.assertFalse(
            Conversation.objects.filter(
                listing=self.listing_no_convo,
                buyer=self.seller,
            ).exists()
        )
