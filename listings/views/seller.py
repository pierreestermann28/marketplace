from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, ListView, UpdateView

from ingestion.models import DetectedItem
from listings.forms import ListingForm, PhotoUploadForm
from listings.models import Listing, ListingReminder
from listings.services import (
    accept_reservation,
    add_images_to_listing,
    archive_listing,
    cancel_reservation,
    create_listing_with_images,
    mark_sold,
    moderate_approve,
    moderate_reject,
    reactivate_listing,
    register_listing_reminder,
    submit_for_review,
)
from listings.services.reservations import (
    ReservationError,
    ReservationInvalid,
    ReservationNotFound,
)
from listings.views.public import get_listing_detail_url


class ListingStartView(LoginRequiredMixin, FormView):
    template_name = "sell/upload_photos.html"
    form_class = PhotoUploadForm

    def form_valid(self, form):
        images = form.cleaned_data["images"]
        primary_index = self._parse_primary_index()
        listing = create_listing_with_images(
            seller=self.request.user,
            images=images,
            primary_index=primary_index,
        )
        return redirect("listing_submit", pk=listing.id)

    def _parse_primary_index(self):
        primary_index = self.request.POST.get("primary_index")
        try:
            return int(primary_index)
        except (TypeError, ValueError):
            return 0


class PhotoUploadView(LoginRequiredMixin, FormView):
    template_name = "sell/upload_photos.html"
    form_class = PhotoUploadForm

    def dispatch(self, request, *args, **kwargs):
        self.listing = get_object_or_404(Listing, id=kwargs["pk"], seller=request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        images = self.request.FILES.getlist("images")
        add_images_to_listing(listing=self.listing, images=images)
        return redirect("listing_submit", pk=self.listing.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["listing"] = self.listing
        context["images"] = [
            li.image_asset.image
            for li in self.listing.images.select_related("image_asset")
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
        submit_for_review(listing=listing, user=self.request.user)
        return redirect("my_listings")


class ReviewQueueView(UserPassesTestMixin, ListView):
    model = Listing
    template_name = "moderation/review_queue.html"
    context_object_name = "listings"

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return (
            Listing.objects.filter(
                Q(status=Listing.Status.PENDING_REVIEW) | Q(needs_review=True)
            )
            .select_related("seller", "category")
            .order_by("created_at")
        )

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        listing_id = request.POST.get("listing_id")
        listing = get_object_or_404(Listing, pk=listing_id)
        if action == "approve":
            moderate_approve(listing=listing, admin_user=request.user)
            django_messages.success(
                request,
                f"L'annonce «{listing.title or listing.id}» est validée et repasse en ligne.",
            )
        elif action == "reject":
            note = request.POST.get("note", "").strip()
            moderate_reject(listing=listing, admin_user=request.user, notes=note)
            django_messages.success(
                request, f"L'annonce «{listing.title or listing.id}» est refusée."
            )
        else:
            django_messages.error(request, "Action inconnue.")
        return redirect("review_queue")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_ia_count"] = DetectedItem.objects.filter(
            status=DetectedItem.Status.USER_APPROVED
        ).count()
        context["admin_swipe_url"] = reverse("operations:dashboard")
        return context


class ReservationCancelView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(
            Listing, id=kwargs["listing_id"], seller=request.user
        )
        detail_url = get_listing_detail_url(listing)
        try:
            cancel_reservation(listing=listing, seller=request.user)
        except ReservationNotFound:
            django_messages.info(request, "Il n’y a plus de réservation active.")
            return redirect(detail_url)
        except ReservationError:
            django_messages.error(request, "Impossible d'annuler la réservation.")
            return redirect(detail_url)

        django_messages.success(request, "La réservation a été annulée.")
        return redirect(detail_url)


class ReservationAcceptView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(
            Listing, id=kwargs["listing_id"], seller=request.user
        )
        detail_url = get_listing_detail_url(listing)
        try:
            accept_reservation(listing=listing, seller=request.user)
        except ReservationNotFound:
            django_messages.info(request, "Il n’y a plus de réservation active.")
            return redirect(detail_url)
        except ReservationInvalid:
            django_messages.info(
                request, "La réservation a déjà été validée ou le statut a changé."
            )
            return redirect(detail_url)
        except ReservationError:
            django_messages.error(request, "Erreur lors de l’acceptation.")
            return redirect(detail_url)

        django_messages.success(
            request,
            "La réservation a été acceptée et l’objet passe en statut Réservation acceptée.",
        )
        return redirect(detail_url)


class ListingActionView(LoginRequiredMixin, View):
    service = None
    success_message = ""

    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(
            Listing, id=kwargs["listing_id"], seller=request.user
        )
        if not self.service:
            return redirect(get_listing_detail_url(listing))
        service = getattr(type(self), "service")
        service(listing=listing, user=request.user)
        django_messages.success(request, self.success_message)
        return redirect(get_listing_detail_url(listing))


class ListingMarkSoldView(ListingActionView):
    service = mark_sold
    success_message = "Annonce marquée comme vendue."


class ListingArchiveView(ListingActionView):
    service = archive_listing
    success_message = "Annonce archivée."


class ListingUnarchiveView(ListingActionView):
    service = reactivate_listing
    success_message = "Annonce réactivée."


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
            moderate_approve(listing=listing, admin_user=request.user)
        elif action == "reject":
            moderate_reject(listing=listing, admin_user=request.user, notes=notes)
        return redirect("review_queue")


class ListingReminderCreateView(LoginRequiredMixin, View):
    def post(self, request, listing_id, *args, **kwargs):
        listing = get_object_or_404(Listing, id=listing_id)
        created = register_listing_reminder(listing=listing, user=request.user)
        if created:
            django_messages.success(
                request, "Nous vous préviendrons dès que l’annonce sera disponible."
            )
        else:
            django_messages.info(request, "Vous êtes déjà inscrit pour être prévenu.")
        return redirect(get_listing_detail_url(listing))
