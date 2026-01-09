from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, FormView, ListView, TemplateView, UpdateView

from mediahub.models import ImageAsset

from .forms import ListingForm, PhotoUploadForm
from .models import Listing, ListingImage


class HomeFeedView(ListView):
    model = Listing
    template_name = "pages/home.html"
    context_object_name = "listings"
    paginate_by = 24

    def get_queryset(self):
        image_qs = ListingImage.objects.select_related("image_asset").order_by("-is_primary", "sort_order")
        return (
            Listing.objects.filter(status=Listing.Status.PUBLISHED)
            .select_related("category", "seller")
            .prefetch_related(Prefetch("images", queryset=image_qs))
            .order_by("-created_at")
        )


class ListingDetailView(DetailView):
    model = Listing
    template_name = "pages/listing_detail.html"
    context_object_name = "listing"

    def get_queryset(self):
        return (
            Listing.objects.select_related("category", "seller")
            .prefetch_related("images__image_asset")
        )

    def get_object(self, queryset=None):
        slug = self.kwargs["slug"]
        listing_id = self.kwargs["uuid"]
        return get_object_or_404(self.get_queryset(), id=listing_id, slug=slug)


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
