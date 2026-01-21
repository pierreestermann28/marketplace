from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.views.generic import TemplateView

from messaging.forms import MessageForm
from messaging.models import Conversation
from messaging.services import get_other_user, mark_messages_read
from messaging.views.common import CONVERSATION_RATE_LIMIT, CONVERSATION_RATE_WINDOW, increment_rate
from reports.forms import ReportForm


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
