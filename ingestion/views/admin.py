from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from billing.entitlements import QuotaExceeded
from ingestion.models import DetectedItem
from ingestion.queries import get_admin_counts, get_next_admin_item
from ingestion.services import items, publishing
from ingestion.views.actions import DetectedItemActionMixin


def _render_quota_prompt(request, item, message):
    context = get_admin_counts()
    context["current_item"] = item
    context["quota_error_message"] = message
    context["upgrade_url"] = getattr(settings, "PREMIUM_UPGRADE_URL", "/pricing")
    return render(request, "fragments/ingestion/quota_upgrade.html", context)


class AdminSwipeView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        return redirect("operations:dashboard")


class AdminSwipeFragmentView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        next_item = get_next_admin_item()
        context = get_admin_counts()
        context["current_item"] = next_item
        template = (
            "fragments/ingestion/admin_swipe_card.html"
            if next_item
            else "fragments/ingestion/admin_swipe_empty.html"
        )
        return render(request, template, context)


class DetectedItemAdminActionMixin(DetectedItemActionMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

    def get_item(self):
        return get_object_or_404(
            DetectedItem.objects.select_related("batch", "hero_asset__image_asset"),
            id=self.kwargs[self.item_kwarg],
        )

    def render_admin_card(self, request):
        next_item = get_next_admin_item()
        context = get_admin_counts()
        context["current_item"] = next_item
        template = (
            "fragments/ingestion/admin_swipe_card.html"
            if next_item
            else "fragments/ingestion/admin_swipe_empty.html"
        )
        return render(request, template, context)


class DetectedItemAdminApproveView(DetectedItemAdminActionMixin, View):
    def post(self, request, *args, **kwargs):
        item = self.get_item()
        if item.status != DetectedItem.Status.USER_APPROVED:
            return self.render_admin_card(request)

        try:
            with transaction.atomic():
                listing = publishing.publish_detected_item(item, skip_quota=True)
                item.listing = listing
                item.save(update_fields=["listing"])
                items.admin_approve(item=item)
        except QuotaExceeded as exc:
            return _render_quota_prompt(request, item, str(exc))
        return self.render_admin_card(request)


class DetectedItemAdminRejectView(DetectedItemAdminActionMixin, View):
    def post(self, request, *args, **kwargs):
        item = self.get_item()
        if item.status != DetectedItem.Status.USER_APPROVED:
            return self.render_admin_card(request)
        items.admin_reject(item=item)
        return self.render_admin_card(request)
