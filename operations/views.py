from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView

from commerce.models import Dispute, Order
from ingestion.models import DetectedItem
from listings.models import Listing


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
            status__in=[Order.Status.DISPUTE, Order.Status.EXPIRED, Order.Status.CANCELLED]
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
