from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from messaging.models import Conversation
from messaging.services.reservations import create_reservation_from_conversation


class SellerReservationCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation.objects.select_related("listing", "buyer", "seller"),
            pk=kwargs["pk"],
        )
        listing = conversation.listing
        if request.user != listing.seller:
            return redirect(reverse("messages:detail", kwargs={"pk": conversation.pk}))
        try:
            create_reservation_from_conversation(
                conversation=conversation,
                note=request.POST.get("reservation_note", "").strip(),
            )
        except Exception as exc:
            django_messages.info(request, str(exc))
            return redirect(reverse("messages:detail", kwargs={"pk": conversation.pk}))
        django_messages.success(
            request, "Réservation enregistrée (non contractuelle) pour cet acheteur."
        )
        return redirect(reverse("messages:detail", kwargs={"pk": conversation.pk}))
