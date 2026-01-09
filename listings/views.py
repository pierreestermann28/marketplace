from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import BooleanField, Exists, OuterRef, Prefetch, Q, Value
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView, UpdateView

from mediahub.models import ImageAsset

from catalog.models import Category

from .forms import ListingForm, PhotoUploadForm
from .models import Favorite, Listing, ListingImage


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
            Listing.objects.filter(status=Listing.Status.PUBLISHED)
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
        context.update(
            {
                "primary_image": primary_image,
                "gallery_images": secondary_images,
                "location_label": self._build_location_label(listing),
                "seller_display_name": listing.seller.get_full_name()
                or listing.seller.username,
                "seller_reputation": getattr(listing.seller, "trust_score", None),
                "fulfillment_modes": self._build_fulfillment_modes(listing),
                "contact_url": reverse("messages:start", kwargs={"listing_id": listing.id}),
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


class MyListingsView(LoginRequiredMixin, ListView):
    model = Listing
    template_name = "sell/my_listings.html"
    context_object_name = "listings"

    def get_queryset(self):
        return (
            Listing.objects.filter(seller=self.request.user)
            .select_related("category")
            .order_by("-created_at")
        )


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

    def post(self, request, *args, **kwargs):
        listing_id = request.POST.get("listing_id")
        action = request.POST.get("action")
        listing = get_object_or_404(Listing, id=listing_id)
        if action == "approve":
            listing.status = Listing.Status.PUBLISHED
        elif action == "reject":
            listing.status = Listing.Status.REJECTED
        listing.moderated_by = request.user
        listing.moderated_at = timezone.now()
        listing.save(update_fields=["status", "moderated_by", "moderated_at"])
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
            return render(
                request,
                "components/listings/favorite_button.html",
                {"listing": listing, "next_url": next_url},
            )
        redirect_to = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("home")
        return HttpResponseRedirect(redirect_to)
