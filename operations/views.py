from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from billing.models import UserEntitlement
from listings.models import Listing
from reports.models import Report

from ingestion.queries import get_admin_counts, get_next_admin_item
from .services import (
    get_operation_counts,
    get_pending_review_listings,
    get_recent_batch_summaries,
    get_recent_entitlements,
    handle_admin_listing_action,
    handle_review_action,
    set_premium_status,
)


class ReviewActionMixin:
    def _handle_review_action(self, request):
        action = request.POST.get("action")
        listing_id = request.POST.get("listing_id")
        listing = get_object_or_404(Listing, pk=listing_id)
        note = request.POST.get("note", "").strip()
        message, success = handle_review_action(
            action=action, listing=listing, admin_user=request.user, note=note
        )
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect(self._return_url())

    def _return_url(self):
        return reverse("operations:dashboard")


class OperationsDashboardView(UserPassesTestMixin, TemplateView):
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


class AdminListingModerationView(UserPassesTestMixin, TemplateView):
    template_name = "moderation/admin_listings.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        status_filter = self.request.GET.get("status")
        valid_statuses = {value for value, _ in Listing.Status.choices}
        qs = (
            Listing.objects.select_related("seller")
            .prefetch_related("reports", "images")
            .order_by("-updated_at")
        )
        if status_filter in valid_statuses:
            qs = qs.filter(status=status_filter)
        return qs[:60]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status_counts = Listing.objects.values("status").annotate(count=Count("id"))
        counts_map = {entry["status"]: entry["count"] for entry in status_counts}
        context.update(
            {
                "listings": self.get_queryset(),
                "reports": Report.objects.filter(is_resolved=False)
                .select_related("listing__seller", "reporter")
                .order_by("-created_at")[:12],
                "status_filter": self.request.GET.get("status") or "",
                "status_choices_for_filter": [
                    {
                        "value": value,
                        "label": label,
                        "count": counts_map.get(value, 0),
                    }
                    for value, label in Listing.Status.choices
                ],
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        listing_id = request.POST.get("listing_id")
        listing = get_object_or_404(
            Listing.objects.select_related("seller"), pk=listing_id
        )
        note = request.POST.get("note", "").strip()
        message, success = handle_admin_listing_action(
            action=action, listing=listing, admin_user=request.user, note=note
        )
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect(self._return_url())

    def _return_url(self):
        base = reverse("operations:admin_listings")
        query = self.request.GET.urlencode()
        return f"{base}?{query}" if query else base
