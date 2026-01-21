import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from ingestion.models import DetectedItem
from ingestion.services import items
from ingestion.queries import get_next_user_item, get_user_pending_items
from ingestion.views.constants import SWIPE_PREFETCH_LIMIT


def _render_swipe_response(request, next_item):
    if next_item:
        html = render_to_string(
            "fragments/ingestion/swipe_deck_card.html",
            {"item": next_item},
            request=request,
        )
        return html, False
    html = render_to_string("fragments/ingestion/swipe_empty.html", request=request)
    return html, True


class SwipeListView(LoginRequiredMixin, TemplateView):
    template_name = "ingestion/swipe.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pending_qs = get_user_pending_items(self.request.user)
        context["items"] = list(pending_qs[:SWIPE_PREFETCH_LIMIT])
        context["pending_count"] = pending_qs.count()
        return context


class SwipeDecisionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            payload = request.POST
        item_id = payload.get("item_id")
        decision = payload.get("decision")
        if not item_id or decision not in {"keep", "reject", "snooze"}:
            return HttpResponseBadRequest("Décision invalide")
        item = get_object_or_404(DetectedItem, id=item_id, owner=request.user)
        if item.status != DetectedItem.Status.PENDING:
            return HttpResponse(status=409)
        if decision == "keep":
            items.user_approve(item=item)
        elif decision == "reject":
            items.user_reject(item=item)
        else:
            item.status = DetectedItem.Status.EDITED
            item.save(update_fields=["status", "updated_at"])
        next_item = get_next_user_item(request.user)
        html, empty = _render_swipe_response(request, next_item)
        return HttpResponse(
            json.dumps({"html": html, "empty": empty}),
            content_type="application/json",
        )
