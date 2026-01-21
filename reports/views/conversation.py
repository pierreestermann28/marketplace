from django.shortcuts import get_object_or_404
from django.urls import reverse

from messaging.models import Conversation

from .base import _BaseReportCreateView


class ConversationReportCreateView(_BaseReportCreateView):
    def get_target(self):
        conversation = get_object_or_404(
            Conversation.objects.select_related("listing"), pk=self.kwargs["pk"]
        )
        return conversation

    def get_success_url(self):
        return reverse("messages:detail", kwargs={"pk": self.target.pk})
