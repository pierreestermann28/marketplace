from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import DetailView, TemplateView

from accounts.models import User
from accounts.queries.profile import get_recent_reviews_for_user
from accounts.services.reputation import ensure_reputation_stats


class PersonalProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        stats = ensure_reputation_stats(user=user)
        context.update(
            {
                "object": user,
                "reputation_stats": stats,
                "reviews_received": get_recent_reviews_for_user(user),
            }
        )
        return context


class PublicProfileView(DetailView):
    model = User
    template_name = "accounts/public_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        stats = ensure_reputation_stats(user=user)
        context["reputation_stats"] = stats
        context["reviews_received"] = get_recent_reviews_for_user(user)
        return context


class PricingView(TemplateView):
    template_name = "accounts/pricing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_meta"] = {
            "title": "Swipe2Sell Premium",
            "description": "Débloquez des quotas illimités et une surveillance premium.",
        }
        context["stripe_publishable_key"] = settings.STRIPE_PUBLISHABLE_KEY
        context["checkout_url"] = reverse_lazy("accounts:stripe_checkout_session")
        context["price_id"] = settings.STRIPE_PREMIUM_PRICE_ID
        return context
