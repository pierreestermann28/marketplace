from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView

from messaging.forms import MessageForm
from messaging.models import Conversation
from messaging.services import (
    get_other_user,
    mark_messages_read,
    send_message,
)
from messaging.views.common import (
    MESSAGE_RATE_LIMIT,
    MESSAGE_RATE_WINDOW,
    increment_rate,
    is_blocked_pair,
)
from reports.forms import ReportForm


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
            mark_messages_read(conversation=conversation, user=self.request.user)
        context["form"] = MessageForm(
            conversation=conversation,
            sender=self.request.user,
        )
        other = get_other_user(conversation, self.request.user) if conversation else None
        context["other_user"] = other
        context["other_user_blocked"] = (
            is_blocked_pair(self.request.user, other) if other else False
        )
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
        other = get_other_user(conversation, request.user)
        if is_blocked_pair(request.user, other):
            form.add_error(None, "Cette conversation est bloquée.")
            return self._render_with_form(conversation, form)
        message_count = increment_rate(
            f"message_rate:{request.user.id}", MESSAGE_RATE_WINDOW
        )
        if message_count > MESSAGE_RATE_LIMIT:
            form.add_error(
                None,
                "Vous avez atteint le nombre maximal de messages en 60 secondes.",
            )
            return self._render_with_form(conversation, form)
        if form.is_valid():
            send_message(
                conversation=conversation,
                sender=request.user,
                text=form.cleaned_data["text"],
            )
            if request.headers.get("HX-Request"):
                conversation = self.get_queryset().get(pk=conversation.pk)
                self.object = conversation
                context = self.get_context_data()
                context["form"] = MessageForm(
                    conversation=conversation,
                    sender=self.request.user,
                )
                return self.render_to_response(context)
            return redirect(reverse("messages:detail", kwargs={"pk": conversation.pk}))
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def _render_with_form(self, conversation, form):
        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)
