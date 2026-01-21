from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from billing.models import UserEntitlement

from ingestion.queries import get_admin_counts, get_next_admin_item
from operations.services import (
    get_operation_counts,
    get_pending_review_listings,
    get_recent_batch_summaries,
    get_recent_entitlements,
    set_premium_status,
)
from .mixins import ReviewActionMixin


class OperationsDashboardView(ReviewActionMixin, UserPassesTestMixin, TemplateView):
    template_name = "operations/admin_workroom.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_operation_counts())
        context.update(get_admin_counts())
        context["current_item"] = get_next_admin_item()
        context["pending_review_listings"] = get_pending_review_listings()
        context["batch_summaries"] = get_recent_batch_summaries()
        context["premium_entitlements"] = get_recent_entitlements()
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "toggle_premium":
            return self._handle_premium_toggle(request)
        return ReviewActionMixin._handle_review_action(self, request)

    def _handle_premium_toggle(self, request):
        user_id = request.POST.get("user_id")
        mode = request.POST.get("mode")
        entitlement = get_object_or_404(
            UserEntitlement.objects.select_related("user"), user__id=user_id
        )
        message = set_premium_status(entitlement=entitlement, enable=mode == "enable")
        messages.success(request, message)
        return redirect(self._return_url())
