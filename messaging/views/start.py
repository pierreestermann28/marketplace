from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import RedirectView

from listings.models import Listing
from messaging.services import get_or_create_conversation
from messaging.views.common import (
    CONVERSATION_RATE_LIMIT,
    CONVERSATION_RATE_WINDOW,
    is_blocked_pair,
    increment_rate,
)


class ConversationStartView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        count = increment_rate(
            f"conversation_rate:{self.request.user.id}", CONVERSATION_RATE_WINDOW
        )
        if count > CONVERSATION_RATE_LIMIT:
            django_messages.error(
                self.request,
                "Trop de démarrages de conversation en peu de temps. Retentez dans une heure.",
            )
            return reverse("messages:list")
        listing = get_object_or_404(Listing, id=kwargs["listing_id"])
        if listing.seller == self.request.user:
            django_messages.error(
                self.request, "Vous ne pouvez pas vous contacter vous-même."
            )
            return reverse(
                "listing_detail", kwargs={"slug": listing.slug, "uuid": listing.id}
            )
        if is_blocked_pair(self.request.user, listing.seller):
            django_messages.error(self.request, "Cette conversation est bloquée.")
            return reverse("messages:list")
        conversation, _ = get_or_create_conversation(
            listing=listing,
            buyer=self.request.user,
            seller=listing.seller,
            initial_last_message_at=timezone.now(),
        )
        return f"{reverse('messages:list')}?conversation={conversation.pk}"
