from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from ingestion.queries import get_next_user_item


def _render_swipe_fragment(request, item):
    if item:
        return render(
            request,
            "fragments/ingestion/swipe_card.html",
            {"current_item": item},
        )
    return render(
        request,
        "fragments/ingestion/swipe_empty.html",
    )


class SwipeNextCardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        next_item = get_next_user_item(request.user)
        return _render_swipe_fragment(request, next_item)
