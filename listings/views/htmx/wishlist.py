from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import TemplateView

from listings.forms import SearchAlertForm
from listings.models import Listing, SearchAlert


class WishlistView(LoginRequiredMixin, TemplateView):
    template_name = "listings/wishlist.html"

    def get_listings(self):
        return (
            Listing.objects.filter(
                favorited_by__user=self.request.user,
                status__in=[Listing.Status.PUBLISHED, Listing.Status.RESERVED],
            )
            .select_related("category", "seller")
            .prefetch_related("images__image_asset")
            .order_by("-favorited_by__created_at", "-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        listings = self.get_listings()
        for listing in listings:
            listing.is_favorited = True
        context["listings"] = listings
        context["wishlist_url"] = reverse("wishlist")
        context["search_alerts"] = SearchAlert.objects.filter(
            user=self.request.user
        ).order_by("-created_at")
        context["search_alert_form"] = SearchAlertForm()
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request"):
            return render(
                self.request,
                "fragments/listings/wishlist_panel.html",
                context,
            )
        return super().render_to_response(context, **response_kwargs)
