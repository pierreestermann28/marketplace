import urllib.parse

from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from catalog.services import list_categories
from location.models import City as LocationCity

from listings.forms import SearchAlertForm
from listings.models import Listing, OnboardingProfile, SearchAlert
from listings.services import (
    SearchAlertAlreadyExists,
    SearchAlertNotFound,
    create_onboarding_alerts,
    create_search_alert,
    delete_search_alert,
    toggle_favorite,
    update_onboarding_profile,
)


class OnboardingView(TemplateView):
    template_name = "listings/onboarding.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = list_categories(order_by=["name"])[:12]
        profile = None
        if self.request.user.is_authenticated:
            profile = (
                OnboardingProfile.objects.select_related("user")
                .prefetch_related("categories")
                .filter(user=self.request.user)
                .first()
            )
        context["onboarding_profile"] = profile
        context["onboarding_filters"] = (
            self.request.session.get("onboarding_filters") or {}
        )
        return context

    def post(self, request, *args, **kwargs):
        category_slugs = [
            slug.strip()
            for slug in request.POST.getlist("category_slugs")
            if slug.strip()
        ]
        city = request.POST.get("city", "").strip()
        location_city_id = request.POST.get("location_city") or request.POST.get(
            "location_city_id"
        )
        location_city = (
            LocationCity.objects.filter(id=location_city_id).first()
            if location_city_id
            else None
        )
        radius = request.POST.get("radius", "").strip()
        purpose = request.POST.get("purpose", "both")
        request.session["onboarding_filters"] = {
            "purpose": purpose,
            "categories": category_slugs,
            "city": city,
            "location_city_id": location_city_id or "",
            "radius": radius,
        }

        if request.user.is_authenticated:
            create_onboarding_alerts(
                user=request.user,
                category_slugs=category_slugs,
                location_city=location_city,
            )
            update_onboarding_profile(
                user=request.user,
                purpose=purpose,
                location_city=location_city,
                radius=radius,
                category_slugs=category_slugs,
            )

        params = []
        if city:
            params.append(("city", city))
        if category_slugs:
            params.extend([("category_slugs", slug) for slug in category_slugs])
        if radius:
            params.append(("radius", radius))
        if purpose:
            params.append(("purpose", purpose))
        query = urllib.parse.urlencode(params, doseq=True)
        url = reverse("suggestions")
        if query:
            url = f"{url}?{query}"
        return redirect(url)


class SearchAlertCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = SearchAlertForm(request.POST)
        if not form.is_valid():
            for error in form.errors.values():
                django_messages.error(request, " ".join(error))
            return redirect("wishlist")

        try:
            create_search_alert(
                user=request.user,
                keyword=form.cleaned_data["keyword"],
                location_city=form.cleaned_data["location_city"],
                category=form.cleaned_data["category"],
            )
        except SearchAlertAlreadyExists:
            django_messages.info(request, "Une alerte identique existe déjà pour vous.")
            return redirect("wishlist")

        django_messages.success(
            request,
            "Alerte créée ! On vous envoie un email dès qu’une annonce correspond.",
        )
        return redirect("wishlist")


class SearchAlertDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        return self._delete(request, kwargs["pk"])

    def delete(self, request, *args, **kwargs):
        return self._delete(request, kwargs["pk"])

    def _delete(self, request, pk):
        try:
            delete_search_alert(alert_id=pk, user=request.user)
        except SearchAlertNotFound:
            raise Http404

        if not request.headers.get("HX-Request"):
            django_messages.success(request, "Alerte supprimée.")
            return redirect("wishlist")
        search_alerts = SearchAlert.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        return render(
            request,
            "fragments/search_alerts/container.html",
            {"search_alerts": search_alerts},
        )


class ListingFavoriteToggleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(Listing, id=kwargs["listing_id"])
        created = toggle_favorite(listing=listing, user=request.user)
        listing.is_favorited = created
        if request.headers.get("HX-Request"):
            next_url = (
                request.POST.get("next")
                or request.META.get("HTTP_REFERER")
                or reverse("home")
            )
            response = render(
                request,
                "components/listings/favorite_button.html",
                {"listing": listing, "next_url": next_url},
            )
            if request.POST.get("wishlist_origin"):
                response["HX-Trigger"] = "wishlist-updated"
            return response
        redirect_to = (
            request.POST.get("next")
            or request.META.get("HTTP_REFERER")
            or reverse("home")
        )
        return HttpResponseRedirect(redirect_to)
