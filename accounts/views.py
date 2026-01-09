from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView

from .models import ReputationStats, User


class ProfileDetailView(DetailView):
    model = User
    template_name = "accounts/profile.html"
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        stats = getattr(user, "reputation", None)
        if not stats:
            stats = ReputationStats.for_user(user)
        context["reputation_stats"] = stats
        context["reviews_received"] = user.reviews_received.select_related("order__listing").order_by("-created_at")[:5]
        return context
