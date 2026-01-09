from datetime import timedelta

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import BooleanField, Exists, OuterRef, Prefetch, Q, Value
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView, UpdateView

from mediahub.models import ImageAsset

from catalog.models import Category

from .forms import ListingForm, PhotoUploadForm
from accounts.models import ReputationStats
from .models import Favorite, Listing, ListingImage, Reservation


def get_listing_detail_url(listing):
    slug = listing.slug or "item"
    return reverse("listing_detail", kwargs={"slug": slug, "uuid": listing.id})


class HomeFeedView(ListView):
    model = Listing
    template_name = "pages/home.html"
    context_object_name = "listings"
    paginate_by = 24

    def get_queryset(self):
        qs = Listing.objects.filter(status=Listing.Status.PUBLISHED)
        q = self.request.GET.get("q", "").strip()
        city = self.request.GET.get("city", "").strip()
        category = self.request.GET.get("category", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if city:
            qs = qs.filter(city__icontains=city)
        if category:
            qs = qs.filter(category__slug=category)
        image_qs = ListingImage.objects.select_related("image_asset").order_by("-is_primary", "sort_order")
        if self.request.user.is_authenticated:
            qs = qs.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(user=self.request.user, listing=OuterRef("pk"))
                )
            )
        else:
            qs = qs.annotate(is_favorited=Value(False, output_field=BooleanField()))
        return qs.select_related("category", "seller").prefetch_related(
            Prefetch("images", queryset=image_qs)
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["filters"] = {
            "q": self.request.GET.get("q", ""),
            "city": self.request.GET.get("city", ""),
            "category": self.request.GET.get("category", ""),
            "querystring": self._get_filter_querystring(),
        }
        return context

    def _get_filter_querystring(self):
        params = self.request.GET.copy()
        params.pop("page", None)
        return params.urlencode()


class ListingDetailView(DetailView):
    model = Listing
    template_name = "pages/listing_detail.html"
    context_object_name = "listing"

    def get_queryset(self):
        qs = (
            Listing.objects.filter(status__in=[Listing.Status.PUBLISHED, Listing.Status.RESERVED])
            .select_related("category", "seller")
            .prefetch_related("images__image_asset")
        )
        if self.request.user.is_authenticated:
            qs = qs.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(user=self.request.user, listing=OuterRef("pk"))
                )
            )
        else:
            qs = qs.annotate(is_favorited=Value(False, output_field=BooleanField()))
        return qs

    def get_object(self, queryset=None):
        slug = self.kwargs["slug"]
        listing_id = self.kwargs["uuid"]
        return get_object_or_404(self.get_queryset(), id=listing_id, slug=slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        listing = context["listing"]
        primary_image = listing.get_primary_image()
        gallery_images = list(listing.images.all())
        secondary_images = [
            image for image in gallery_images if image != primary_image
        ]
        photo_gallery = [primary_image] + secondary_images if primary_image else secondary_images
        active_reservation = listing.refresh_reservation_state()
        stats = getattr(listing.seller, "reputation", None)
        if not stats:
            stats = ReputationStats.for_user(listing.seller)
        context.update(
            {
                "primary_image": primary_image,
                "gallery_images": secondary_images,
                "photo_gallery": photo_gallery,
                "location_label": self._build_location_label(listing),
                "seller_display_name": listing.seller.get_full_name()
                or listing.seller.username,
                "seller_reputation": getattr(listing.seller, "trust_score", None),
                "seller_reputation_stats": stats,
                "condition_display": listing.get_condition_display() or listing.condition,
                "fulfillment_modes": self._build_fulfillment_modes(listing),
                "contact_url": reverse("messages:start", kwargs={"listing_id": listing.id}),
                "active_reservation": active_reservation,
                "reservation_expiration_hours": getattr(settings, "RESERVATION_HOLD_HOURS", 24),
                "reserve_url": reverse("listing_reserve", kwargs={"listing_id": listing.id}),
                "cancel_reservation_url": reverse("listing_cancel_reservation", kwargs={"listing_id": listing.id}),
                "can_reserve": listing.status == Listing.Status.PUBLISHED
                and self.request.user.is_authenticated
                and self.request.user != listing.seller,
            }
        )
        return context

    def _build_location_label(self, listing):
        parts = [listing.city, listing.postal_code]
        return ", ".join(filter(None, parts)) or listing.country_code

    def _build_fulfillment_modes(self, listing):
        modes = []
        if listing.shipping_enabled:
            modes.append(
                {
                    "label": "Livraison sécurisée",
                    "detail": "Expédition suivie et assurance incluse",
                }
            )
        if listing.in_person_enabled:
            modes.append(
                {
                    "label": "Remise en main propre",
                    "detail": "Retrait sur rendez-vous local",
                }
            )
        return modes


class WishlistView(LoginRequiredMixin, TemplateView):
    template_name = "pages/wishlist.html"

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
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request"):
            return render(
                self.request,
                "fragments/listings/wishlist_panel.html",
                context,
            )
        return super().render_to_response(context, **response_kwargs)


class MyListingsView(LoginRequiredMixin, ListView):
    model = Listing
    template_name = "sell/my_listings.html"
    context_object_name = "listings"

    def get_queryset(self):
        reservation_qs = Reservation.objects.active().select_related("buyer")
        return (
            Listing.objects.filter(seller=self.request.user)
            .select_related("category")
            .prefetch_related("images__image_asset", Prefetch("reservations", queryset=reservation_qs))
            .order_by("-updated_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for listing in context["listings"]:
            listing.active_reservation = listing.refresh_reservation_state()
        context["reservation_expiration_hours"] = getattr(settings, "RESERVATION_HOLD_HOURS", 24)
        return context


class ListingStartView(LoginRequiredMixin, FormView):
    template_name = "sell/upload_photos.html"
    form_class = PhotoUploadForm

    def form_valid(self, form):
        listing = Listing.objects.create(
            seller=self.request.user,
            status=Listing.Status.DRAFT,
            currency="EUR",
        )
        images = form.cleaned_data["images"]
        primary_index = self.request.POST.get("primary_index")
        try:
            primary_index = int(primary_index)
        except (TypeError, ValueError):
            primary_index = 0
        for image in images:
            asset = ImageAsset.objects.create(user=self.request.user, image=image)
            ListingImage.objects.create(
                listing=listing,
                image_asset=asset,
                is_primary=False,
                sort_order=0,
            )
        listing_images = list(listing.images.all())
        for idx, listing_image in enumerate(listing_images):
            listing_image.sort_order = idx
            listing_image.is_primary = idx == primary_index
            listing_image.save(update_fields=["sort_order", "is_primary"])
        return HttpResponseRedirect(reverse("listing_submit", kwargs={"pk": listing.id}))


class PhotoUploadView(LoginRequiredMixin, FormView):
    template_name = "sell/upload_photos.html"
    form_class = PhotoUploadForm

    def dispatch(self, request, *args, **kwargs):
        self.listing = get_object_or_404(
            Listing, id=kwargs["pk"], seller=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        images = self.request.FILES.getlist("images")
        for image in images:
            asset = ImageAsset.objects.create(user=self.request.user, image=image)
            ListingImage.objects.create(listing=self.listing, image_asset=asset)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("listing_submit", kwargs={"pk": self.listing.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["listing"] = self.listing
        context["images"] = [
            li.image_asset.image for li in self.listing.images.select_related("image_asset")
        ]
        return context


class SubmitForReviewView(LoginRequiredMixin, UpdateView):
    model = Listing
    form_class = ListingForm
    template_name = "sell/submit_for_review.html"

    def get_queryset(self):
        return Listing.objects.filter(seller=self.request.user)

    def form_valid(self, form):
        listing = form.save(commit=False)
        listing.status = Listing.Status.PENDING_REVIEW
        listing.save()
        return HttpResponseRedirect(reverse("my_listings"))


class ReviewQueueView(UserPassesTestMixin, ListView):
    model = Listing
    template_name = "moderation/review_queue.html"
    context_object_name = "listings"

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return (
            Listing.objects.filter(status=Listing.Status.PENDING_REVIEW)
            .select_related("seller", "category")
            .order_by("created_at")
        )


class ReservationCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(Listing, id=kwargs["listing_id"])
        detail_url = get_listing_detail_url(listing)
        if listing.seller == request.user:
            django_messages.error(request, "Vous ne pouvez pas réserver votre propre annonce.")
            return redirect(detail_url)
        active_reservation = listing.refresh_reservation_state()
        if listing.status != Listing.Status.PUBLISHED or active_reservation:
            django_messages.error(request, "Cette annonce n’est pas disponible à la réservation.")
            return redirect(detail_url)
        expires_at = timezone.now() + timedelta(
            hours=getattr(settings, "RESERVATION_HOLD_HOURS", 24)
        )
        Reservation.objects.create(
            listing=listing, buyer=request.user, expires_at=expires_at
        )
        listing.status = Listing.Status.RESERVED
        listing.save(update_fields=["status"])
        django_messages.success(request, "L’annonce a bien été réservée.")
        return redirect(detail_url)


class ReservationCancelView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(Listing, id=kwargs["listing_id"], seller=request.user)
        detail_url = get_listing_detail_url(listing)
        reservation = listing.refresh_reservation_state()
        if not reservation:
            django_messages.info(request, "Il n’y a plus de réservation active.")
            return redirect(detail_url)
        reservation.cancel()
        if listing.status == Listing.Status.RESERVED:
            listing.status = Listing.Status.PUBLISHED
            listing.save(update_fields=["status"])
        django_messages.success(request, "La réservation a été annulée.")
        return redirect(detail_url)


class ListingModerationDetailView(UserPassesTestMixin, DetailView):
    model = Listing
    template_name = "moderation/listing_detail.html"
    context_object_name = "listing"

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return (
            Listing.objects.filter(status=Listing.Status.PENDING_REVIEW)
            .select_related("seller", "category")
            .prefetch_related("images__image_asset")
        )

    def post(self, request, *args, **kwargs):
        listing = self.get_object()
        action = request.POST.get("action")
        notes = request.POST.get("moderation_notes", "").strip()
        if action == "approve":
            listing.status = Listing.Status.PUBLISHED
            listing.moderation_notes = ""
        elif action == "reject":
            listing.status = Listing.Status.REJECTED
            listing.moderation_notes = notes
        listing.moderated_by = request.user
        listing.moderated_at = timezone.now()
        listing.save(
            update_fields=["status", "moderation_notes", "moderated_by", "moderated_at"]
        )
        return HttpResponseRedirect(reverse("review_queue"))


class ListingFavoriteToggleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(Listing, id=kwargs["listing_id"])
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            listing=listing,
        )
        if not created:
            favorite.delete()
        listing.is_favorited = created
        if request.headers.get("HX-Request"):
            next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("home")
            response = render(
                request,
                "components/listings/favorite_button.html",
                {"listing": listing, "next_url": next_url},
            )
            if request.POST.get("wishlist_origin"):
                response["HX-Trigger"] = "wishlist-updated"
            return response
        redirect_to = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("home")
        return HttpResponseRedirect(redirect_to)
