from datetime import timedelta

from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, RedirectView, TemplateView

from listings.models import Listing

from .forms import MessageForm
from .models import Conversation, Message


class ConversationDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "messaging/messages.html"

    def get_conversations(self):
        user = self.request.user
        return (
            Conversation.objects.filter(models.Q(buyer=user) | models.Q(seller=user))
            .select_related("listing", "seller", "buyer")
            .prefetch_related("messages")
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
        context["message_form"] = MessageForm()
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
        context.setdefault("form", MessageForm())
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["messaging/partials/conversation_detail_panel.html"]
        return super().get_template_names()

    def post(self, request, *args, **kwargs):
        conversation = self.get_object()
        self.object = conversation
        form = MessageForm(request.POST)
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
                context["form"] = MessageForm()
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


class ConversationStartView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        listing = get_object_or_404(Listing, id=kwargs["listing_id"])
        if listing.seller == self.request.user:
            django_messages.error(
                self.request, "Vous ne pouvez pas vous contacter vous-même."
            )
            return reverse(
                "listing_detail", kwargs={"slug": listing.slug, "uuid": listing.id}
            )
        conversation, created = Conversation.objects.get_or_create(
            listing=listing,
            buyer=self.request.user,
            defaults={"seller": listing.seller, "last_message_at": timezone.now()},
        )
        return f"{reverse('messages:list')}?conversation={conversation.pk}"


# Create your views here.
