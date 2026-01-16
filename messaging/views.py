from datetime import timedelta

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, RedirectView, TemplateView

from listings.models import Listing, Reservation, ReservationLog

from .forms import MessageForm
from .models import BlockedUser, Conversation, Message
from reports.forms import ReportForm

CONVERSATION_RATE_LIMIT = 5
CONVERSATION_RATE_WINDOW = 3600
MESSAGE_RATE_LIMIT = 20
MESSAGE_RATE_WINDOW = 60


def _increment_rate(key, window):
    count = cache.get(key)
    if count is None:
        cache.set(key, 1, window)
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        return 1


def _is_blocked(sender, receiver):
    return BlockedUser.objects.filter(
        models.Q(blocker=sender, blocked=receiver)
        | models.Q(blocker=receiver, blocked=sender)
    ).exists()


class ConversationDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "messaging/messages.html"

    def get_conversations(self):
        user = self.request.user
        unread_filter = ~models.Q(messages__sender=user) & models.Q(
            messages__is_read=False
        )
        return (
            Conversation.objects.filter(models.Q(buyer=user) | models.Q(seller=user))
            .select_related("listing", "seller", "buyer")
            .prefetch_related("messages")
            .annotate(new_messages_count=models.Count("messages", filter=unread_filter))
            .order_by("-last_message_at", "-created_at")
        )

    def get_default_conversation(self, conversations):
        if not conversations:
            return None
        recent = conversations.filter(last_message_at__isnull=False).order_by(
            "-last_message_at"
        )
        return recent.first() if recent.exists() else conversations.first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversations = self.get_conversations()
        context["conversations"] = conversations
        selected_pk = self.request.GET.get("conversation")
        selected_conversation = (
            conversations.filter(pk=selected_pk).first()
            if selected_pk
            else self.get_default_conversation(conversations)
        )
        context["selected_conversation"] = selected_conversation
        context["selected_conversation_pk"] = (
            selected_conversation.pk if selected_conversation else None
        )
        context["message_form"] = MessageForm(
            conversation=selected_conversation,
            sender=self.request.user,
        )
        return context


class ConversationDetailView(LoginRequiredMixin, DetailView):
    model = Conversation
    template_name = "messaging/conversation_detail.html"
    context_object_name = "conversation"

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(models.Q(buyer=user) | models.Q(seller=user))
            .select_related("listing", "seller", "buyer")
            .prefetch_related("messages", "messages__sender")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = context.get("conversation")
        if conversation:
            conversation.mark_messages_read_for(self.request.user)
        context["form"] = MessageForm(
            conversation=conversation,
            sender=self.request.user,
        )
        other = conversation.other_user(self.request.user) if conversation else None
        context["other_user"] = other
        context["other_user_blocked"] = _is_blocked(self.request.user, other) if other else False
        context["report_form"] = ReportForm()
        context["conversation_report_url"] = (
            reverse("reports:conversation_report", kwargs={"pk": conversation.pk})
            if conversation
            else "#"
        )
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["messaging/partials/conversation_detail_panel.html"]
        return super().get_template_names()

    def post(self, request, *args, **kwargs):
        conversation = self.get_object()
        self.object = conversation
        form = MessageForm(
            request.POST,
            conversation=conversation,
            sender=request.user,
        )
        other = conversation.other_user(request.user)
        if _is_blocked(request.user, other):
            form.add_error(None, "Cette conversation est bloquée.")
            return self._render_with_form(conversation, form)
        message_count = _increment_rate(
            f"message_rate:{request.user.id}", MESSAGE_RATE_WINDOW
        )
        if message_count > MESSAGE_RATE_LIMIT:
            form.add_error(
                None,
                "Vous avez atteint le nombre maximal de messages en 60 secondes.",
            )
            return self._render_with_form(conversation, form)
        if form.is_valid():
            now = timezone.now()
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            conversation.last_message_at = now
            conversation.save(update_fields=["last_message_at"])

            if request.headers.get("HX-Request"):
                conversation = self.get_queryset().get(pk=conversation.pk)
                self.object = conversation
                context = self.get_context_data()
                context["form"] = MessageForm(
                    conversation=conversation,
                    sender=self.request.user,
                )
                return self.render_to_response(
                    context,
                )

            return redirect(reverse("messages:detail", kwargs={"pk": conversation.pk}))

        # Invalid form: return partial for HX, full otherwise
        context = self.get_context_data(form=form)
        if request.headers.get("HX-Request"):
            return self.render_to_response(
                context,
            )
        return self.render_to_response(context)


class SellerReservationCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation.objects.select_related("listing", "buyer", "seller"),
            pk=kwargs["pk"],
        )
        listing = conversation.listing
        if request.user != listing.seller:
            return redirect(
                reverse("messages:detail", kwargs={"pk": conversation.pk})
            )
        if listing.status not in {
            Listing.Status.PUBLISHED,
        }:
            django_messages.info(
                request,
                "La réservation ne peut être initiée que pour une annonce disponible.",
            )
            return redirect(
                reverse("messages:detail", kwargs={"pk": conversation.pk})
            )
        if Reservation.objects.active().filter(listing=listing).exists():
            django_messages.info(
                request, "Il existe déjà une réservation active pour cette annonce."
            )
            return redirect(
                reverse("messages:detail", kwargs={"pk": conversation.pk})
            )
        note = request.POST.get("reservation_note", "").strip()
        expires_at = timezone.now() + timedelta(
            hours=getattr(settings, "RESERVATION_HOLD_HOURS", 24)
        )
        with transaction.atomic():
            Reservation.objects.create(
                listing=listing,
                buyer=conversation.buyer,
                expires_at=expires_at,
            )
            listing.status = Listing.Status.RESERVED
            listing.reserved_for = conversation.buyer
            listing.reserved_at = timezone.now()
            listing.reservation_note = note
            listing.save(
                update_fields=[
                    "status",
                    "reserved_for",
                    "reserved_at",
                    "reservation_note",
                    "updated_at",
                ]
            )
            ReservationLog.objects.create(
                listing=listing,
                user=request.user,
                action=ReservationLog.Action.RESERVED,
                note=note,
            )
        django_messages.success(
            request, "Réservation enregistrée (non contractuelle) pour cet acheteur."
        )
        return redirect(reverse("messages:detail", kwargs={"pk": conversation.pk}))


class ConversationStartView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        count = _increment_rate(
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
        if _is_blocked(self.request.user, listing.seller):
            django_messages.error(
                self.request, "Cette conversation est bloquée."
            )
            return reverse("messages:list")
        conversation, created = Conversation.objects.get_or_create(
            listing=listing,
            buyer=self.request.user,
            defaults={"seller": listing.seller, "last_message_at": timezone.now()},
        )
        return f"{reverse('messages:list')}?conversation={conversation.pk}"


# Create your views here.
