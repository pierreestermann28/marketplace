from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from commerce.models import Dispute, Order
from ingestion.models import DetectedItem
from listings.models import Listing
from reports.models import Report


class OperationsDashboardView(UserPassesTestMixin, TemplateView):
    template_name = "moderation/operations_dashboard.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orders_pending"] = Order.objects.filter(
            status__in=[Order.Status.CREATED, Order.Status.AWAITING_CONFIRMATION]
        ).count()
        context["orders_attention"] = Order.objects.filter(
            status__in=[
                Order.Status.DISPUTE,
                Order.Status.EXPIRED,
                Order.Status.CANCELLED,
            ]
        ).count()
        context["open_disputes"] = Dispute.objects.filter(is_resolved=False).count()
        context["pending_detected_items"] = DetectedItem.objects.filter(
            status=DetectedItem.Status.PENDING
        ).count()
        context["trending_listings"] = (
            Listing.objects.filter(status=Listing.Status.PUBLISHED)
            .order_by("-view_count")
            .select_related("seller")
            .prefetch_related("images")
            .all()[:6]
        )
        return context


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
        if action == "unpublish":
            note = request.POST.get("note", "").strip()
            listing.status = Listing.Status.ARCHIVED
            fields = ["status", "moderated_by", "moderated_at"]
            listing.moderated_by = request.user
            listing.moderated_at = timezone.now()
            if note:
                listing.moderation_notes = note
                fields.append("moderation_notes")
            listing.save(update_fields=fields)
            messages.success(
                request,
                f"L'annonce «{listing.title or listing.id}» est hors ligne.",
            )
        elif action == "ban_user":
            seller = listing.seller
            seller.is_active = False
            seller.save(update_fields=["is_active"])
            messages.success(
                request,
                f"L'utilisateur {seller.get_full_name() or seller.email} est désactivé.",
            )
        else:
            messages.error(request, "Action inconnue.")
        return redirect(self._return_url())

    def _return_url(self):
        base = reverse("operations:admin_listings")
        query = self.request.GET.urlencode()
        return f"{base}?{query}" if query else base
