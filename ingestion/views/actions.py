from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.views import View

from django.contrib.auth.mixins import LoginRequiredMixin

from ingestion.models import DetectedItem
from ingestion.services import items


class DetectedItemActionMixin(LoginRequiredMixin):
    item_kwarg = "item_id"

    def get_item(self):
        return get_object_or_404(
            DetectedItem.objects.select_related("batch", "hero_asset__image_asset"),
            id=self.kwargs[self.item_kwarg],
            owner=self.request.user,
        )

    def get_next_item(self, batch):
        return (
            batch.detected_items.filter(status=DetectedItem.Status.PENDING)
            .select_related("hero_asset__image_asset")
            .order_by("created_at")
            .first()
        )

    def render_next_card(self, request, batch):
        next_item = self.get_next_item(batch)
        if next_item:
            return render(
                request,
                "fragments/ingestion/swipe_card.html",
                {"batch": batch, "current_item": next_item},
            )
        return render(
            request,
            "fragments/ingestion/swipe_empty.html",
            {"batch": batch},
        )


class DetectedItemApproveView(DetectedItemActionMixin, View):
    def post(self, request, *args, **kwargs):
        item = self.get_item()
        if item.status != DetectedItem.Status.PENDING:
            return self.render_next_card(request, item.batch)

        with transaction.atomic():
            items.user_approve(item=item)
        return self.render_next_card(request, item.batch)


class DetectedItemRejectView(DetectedItemActionMixin, View):
    def post(self, request, *args, **kwargs):
        item = self.get_item()
        if item.status != DetectedItem.Status.PENDING:
            return self.render_next_card(request, item.batch)
        items.user_reject(item=item)
        return self.render_next_card(request, item.batch)
