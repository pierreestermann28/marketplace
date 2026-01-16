from datetime import timedelta

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.db.models import Avg, BooleanField, Count, Exists, F, OuterRef, Prefetch, Q, Value
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from mediahub.models import ImageAsset

from catalog.models import Category

from .forms import ListingForm, PhotoUploadForm, SearchAlertForm
from django.utils.text import slugify

from .models import (
    Favorite,
    Listing,
    ListingImage,
    ListingReminder,
    ListingView,
    Reservation,
    ReservationLog,
    SearchAlert,
)
from .utils import user_can_view_contact_info
from accounts.models import ReputationStats
from commerce.models import Review
from ingestion.models import DetectedItem


def get_listing_detail_url(listing):
    slug = listing.slug or "item"
    return reverse("listing_detail", kwargs={"slug": slug, "uuid": listing.id})


class HomeFeedView(ListView):
    model = Listing
    template_name = "pages/home.html"
    context_object_name = "listings"
    paginate_by = 24
    status_filter = [Listing.Status.PUBLISHED]
    default_title = "Annonces responsables | StillUseful"
    default_description = "Vendez et achetez localement avec StillUseful : annonces vérifiées, échanges sécurisés et durabilité."

    def get_queryset(self):
        qs = Listing.objects.filter(status__in=self.status_filter)
        q = self.request.GET.get("q", "").strip()
        city = self.request.GET.get("city", "").strip()
        category = self.request.GET.get("category", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if city:
            qs = qs.filter(city__icontains=city)
        if category:
            qs = qs.filter(category__slug=category)
        image_qs = self._image_prefetch_queryset()
        if self.request.user.is_authenticated:
            qs = qs.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(
                        user=self.request.user, listing=OuterRef("pk")
                    )
                )
            )
            qs = self._annotate_with_seen(qs)
        else:
            qs = qs.annotate(is_favorited=Value(False, output_field=BooleanField()))
            qs = qs.annotate(is_seen=Value(False, output_field=BooleanField()))
        return (
            qs.select_related("category", "seller")
            .prefetch_related(Prefetch("images", queryset=image_qs))
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["filters"] = {
            "q": self.request.GET.get("q", ""),
            "city": self.request.GET.get("city", ""),
            "category": self.request.GET.get("category", ""),
            "querystring": self._get_filter_querystring(),
        }
        context["search_alert_form"] = SearchAlertForm()
        recommended, category_ids = self._get_recommendations()
        context["recommended_listings"] = recommended
        context["recommendation_reason"] = self._build_recommendation_reason(
            category_ids
        )
        context["feed_partial_url"] = self._build_feed_partial_url(context["filters"]["querystring"])
        context["featured_categories"] = (
            Category.objects.filter(listings__status__in=self.status_filter)
            .annotate(count=Count("listings"))
            .order_by("-count")[:6]
        )
        featured_city_qs = (
            Listing.objects.filter(status__in=self.status_filter)
            .exclude(city__exact="")
            .values("city")
            .annotate(count=Count("id"))
            .order_by("-count")[:6]
        )
        context["featured_cities"] = [
            {"city": city["city"], "count": city["count"], "slug": slugify(city["city"])}
            for city in featured_city_qs
        ]
        context["page_meta"] = self._default_page_meta()
        context["page_heading"] = "Annonces locales"
        context["page_description"] = context["page_meta"]["description"]
        page_obj = context.get("page_obj")
        current_page = page_obj.number if page_obj else None
        context["canonical_url"] = self._build_canonical_url(current_page)
        context["pagination_links"] = self._build_pagination_links(page_obj)
        return context

    def _get_filter_querystring(self):
        params = self.request.GET.copy()
        params.pop("page", None)
        return params.urlencode()

    def _image_prefetch_queryset(self):
        return ListingImage.objects.select_related("image_asset").order_by(
            "-is_primary", "sort_order"
        )

    def _get_recommendations(self):
        user = self.request.user
        if not user.is_authenticated:
            return [], []

        fav_categories = list(
            Favorite.objects.filter(user=user)
            .exclude(listing__category__isnull=True)
            .values_list("listing__category", flat=True)
        )
        reserved_categories = list(
            Reservation.objects.filter(
                buyer=user, cancelled_at__isnull=True
            )
            .exclude(listing__category__isnull=True)
            .values_list("listing__category", flat=True)
        )
        category_ids = list({*fav_categories, *reserved_categories})
        if not category_ids:
            return [], []

        qs = (
            Listing.objects.filter(
                status=Listing.Status.PUBLISHED, category_id__in=category_ids
            )
            .select_related("category", "seller")
            .prefetch_related(
                Prefetch("images", queryset=self._image_prefetch_queryset())
            )
            .order_by("-created_at")
        )
        qs = self._annotate_with_seen(qs)
        return list(qs[:6]), category_ids

    def _build_recommendation_reason(self, category_ids):
        if not category_ids:
            return "vos favoris"
        category = (
            Category.objects.filter(id__in=category_ids).order_by("name").first()
        )
        if category:
            return f"vos favoris dans {category.name}"
        return "vos favoris"

    def _build_feed_partial_url(self, querystring):
        base = reverse("home_feed_partial")
        if querystring:
            return f"{base}?{querystring}"
        return base

    def _annotate_with_seen(self, qs):
        user = self.request.user
        if not user.is_authenticated:
            return qs
        seen_qs = ListingView.objects.filter(user=user, listing=OuterRef("pk"))
        return qs.annotate(is_seen=Exists(seen_qs))

    def _default_page_meta(self):
        return {
            "title": self.default_title,
            "description": self.default_description,
            "og_title": self.default_title,
            "og_description": self.default_description,
            "og_type": "website",
        }

    def _build_canonical_url(self, page_number=None):
        query = self._get_filter_querystring()
        if page_number and page_number > 1:
            suffix = f"page={page_number}"
            query = f"{query}&{suffix}" if query else suffix
        path = self.request.path
        canonical = self.request.build_absolute_uri(path)
        if query:
            return f"{canonical}?{query}"
        return canonical

    def _build_pagination_links(self, page_obj):
        links = {}
        if not page_obj:
            return links
        if page_obj.has_previous():
            links["prev"] = self._build_canonical_url(page_obj.previous_page_number())
        if page_obj.has_next():
            links["next"] = self._build_canonical_url(page_obj.next_page_number())
        return links


class HomeFeedPartialView(HomeFeedView):
    template_name = "components/listings/listing_grid.html"
    paginate_by = 24
    context_object_name = "listings"

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return render(request, self.get_template_names(), context)


class CategoryListingView(HomeFeedView):
    template_name = "pages/listings_feed.html"

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category, slug=kwargs["slug"])
        query_params = request.GET.copy()
        query_params["category"] = self.category.slug
        request.GET = query_params
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        description = f"Explorez toutes les annonces {self.category.name} vérifiées sur StillUseful."
        context["page_heading"] = f"Catégorie {self.category.name}"
        context["page_description"] = description
        context["page_meta"] = {
            "title": f"{self.category.name} | StillUseful",
            "description": description,
            "og_title": f"{self.category.name} – StillUseful",
            "og_description": description,
            "og_type": "website",
        }
        return context


class CityListingView(HomeFeedView):
    template_name = "pages/listings_feed.html"

    def dispatch(self, request, *args, **kwargs):
        self.city_label = self._resolve_city(kwargs["slug"])
        query_params = request.GET.copy()
        query_params["city"] = self.city_label
        request.GET = query_params
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        description = f"Les meilleures annonces disponibles à {self.city_label}."
        context["page_heading"] = f"{self.city_label}"
        context["page_description"] = description
        context["page_meta"] = {
            "title": f"Annonces à {self.city_label} | StillUseful",
            "description": description,
            "og_title": f"Annonces à {self.city_label}",
            "og_description": description,
            "og_type": "website",
        }
        return context

    def _resolve_city(self, slug):
        cities = (
            Listing.objects.filter(city__isnull=False)
            .exclude(city="")
            .values_list("city", flat=True)
            .distinct()
        )
        for city in cities:
            if slugify(city) == slug:
                return city
        raise Http404("Ville inconnue")


class ListingDetailView(DetailView):
    model = Listing
    template_name = "pages/listing_detail.html"
    context_object_name = "listing"

    def get_queryset(self):
        qs = (
            Listing.objects.filter(
                status__in=[
                    Listing.Status.PUBLISHED,
                    Listing.Status.RESERVED,
                    Listing.Status.RESERVATION_ACCEPTED,
                ]
            )
            .select_related("category", "seller")
            .prefetch_related("images__image_asset")
        )
        if self.request.user.is_authenticated:
            qs = qs.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(
                        user=self.request.user, listing=OuterRef("pk")
                    )
                )
            )
        else:
            qs = qs.annotate(is_favorited=Value(False, output_field=BooleanField()))
        return qs

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        canonical_slug = self.object.slug or "item"
        if kwargs.get("slug") != canonical_slug:
            return redirect(get_listing_detail_url(self.object))
        return super().get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        listing_id = self.kwargs["uuid"]
        queryset = queryset or self.get_queryset()
        return get_object_or_404(queryset, id=listing_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        listing = context["listing"]
        listing.increment_view_count()
        if self.request.user.is_authenticated:
            ListingView.objects.update_or_create(
                user=self.request.user,
                listing=listing,
                defaults={"viewed_at": timezone.now()},
            )
        primary_image = listing.get_primary_image()
        gallery_images = list(listing.images.all())
        secondary_images = [image for image in gallery_images if image != primary_image]
        photo_gallery = (
            [primary_image] + secondary_images if primary_image else secondary_images
        )
        active_reservation = listing.refresh_reservation_state()
        stats = getattr(listing.seller, "reputation", None)
        if not stats:
            stats = ReputationStats.for_user(listing.seller)
        review_stats = self._build_seller_review_stats(listing.seller)
        listing_url = get_listing_detail_url(listing)
        context.update(
            {
                "primary_image": primary_image,
                "gallery_images": secondary_images,
                "photo_gallery": photo_gallery,
                "location_label": self._build_location_label(listing),
                "seller_display_name": listing.seller.get_full_name()
                or listing.seller.email,
                "seller_reputation": getattr(listing.seller, "trust_score", None),
                "seller_reputation_stats": review_stats,
                "condition_display": listing.get_condition_display()
                or listing.condition,
                "fulfillment_modes": self._build_fulfillment_modes(listing),
                "contact_url": reverse(
                    "messages:start", kwargs={"listing_id": listing.id}
                ),
                "active_reservation": active_reservation,
                "reservation_expiration_hours": getattr(
                    settings, "RESERVATION_HOLD_HOURS", 24
                ),
                "cancel_reservation_url": reverse(
                    "listing_cancel_reservation", kwargs={"listing_id": listing.id}
                ),
                "available_from": listing.available_from,
                "view_count": listing.view_count,
                "remind_url": (
                    reverse(
                        "listing_remind", kwargs={"listing_id": listing.id}
                    )
                    if listing.available_from and self.request.user.is_authenticated
                    else None
                ),
                "reminder_exists": (
                    self.request.user.is_authenticated
                    and ListingReminder.objects.filter(
                        user=self.request.user, listing=listing
                    ).exists()
                ),
                "can_view_contact_info": user_can_view_contact_info(
                    self.request.user, listing
                ),
                "contact_lock_reason": (
                    "Les coordonnées se débloquent après une réservation ou un paiement validé."
                ),
            }
        )
        context["page_meta"] = {
            "title": f"{listing.title} | StillUseful",
            "description": (listing.description or listing.title)[:160],
            "og_title": listing.title,
            "og_description": (listing.description or listing.title)[:200],
            "og_type": "product",
        }
        context["canonical_url"] = self.request.build_absolute_uri(listing_url)
        context["pagination_links"] = {}
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

    def _build_seller_review_stats(self, seller):
        seller_reviews = seller.reviews_received.filter(
            role=Review.Role.BUYER_TO_SELLER
        )
        buyer_reviews = seller.reviews_received.filter(
            role=Review.Role.SELLER_TO_BUYER
        )
        seller_avg = seller_reviews.aggregate(avg=Avg("rating"))["avg"]
        buyer_avg = buyer_reviews.aggregate(avg=Avg("rating"))["avg"]
        return {
            "seller_rating_avg": seller_avg or 0,
            "seller_rating_count": seller_reviews.count(),
            "items_sold_count": seller_reviews.count(),
            "buyer_rating_avg": buyer_avg or 0,
            "buyer_rating_count": buyer_reviews.count(),
        }


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
        context["search_alerts"] = SearchAlert.objects.filter(user=self.request.user).order_by("-created_at")
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


class SearchAlertCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = SearchAlertForm(request.POST)
        if form.is_valid():
            alert, created = SearchAlert.objects.get_or_create(
                user=request.user,
                keyword=form.cleaned_data["keyword"],
                city=form.cleaned_data["city"],
                category=form.cleaned_data["category"],
                defaults={"is_active": True},
            )
            if created:
                django_messages.success(
                    request,
                    "Alerte créée ! On vous envoie un email dès qu’une annonce correspond.",
                )
            else:
                django_messages.info(
                    request, "Une alerte identique existe déjà pour vous."
                )
        else:
            for error in form.errors.values():
                django_messages.error(request, " ".join(error))
        return redirect("wishlist")


class MyListingsView(LoginRequiredMixin, ListView):
    model = Listing
    template_name = "sell/my_listings.html"
    context_object_name = "listings"
 
    STATUS_ORDER = [
        Listing.Status.DRAFT,
        Listing.Status.PENDING_REVIEW,
        Listing.Status.PUBLISHED,
        Listing.Status.RESERVED,
        Listing.Status.RESERVATION_ACCEPTED,
        Listing.Status.SOLD,
        Listing.Status.REJECTED,
        Listing.Status.ARCHIVED,
    ]

    STATUS_LABELS = {
        Listing.Status.DRAFT: "Brouillons",
        Listing.Status.PENDING_REVIEW: "En relecture",
        Listing.Status.PUBLISHED: "Publiés",
        Listing.Status.RESERVED: "Réservés",
        Listing.Status.RESERVATION_ACCEPTED: "Réservation acceptée",
        Listing.Status.SOLD: "Vendues",
        Listing.Status.REJECTED: "Refusés",
        Listing.Status.ARCHIVED: "Archivée",
    }

    STATUS_DESCRIPTIONS = {
        Listing.Status.DRAFT: "Complète les infos",
        Listing.Status.PENDING_REVIEW: "Sous validation équipe",
        Listing.Status.PUBLISHED: "Visibles par tous",
        Listing.Status.RESERVED: "Attente confirmation",
        Listing.Status.RESERVATION_ACCEPTED: "Réservation validée",
        Listing.Status.SOLD: "Livrées ou payées",
        Listing.Status.REJECTED: "Demande une mise à jour",
        Listing.Status.ARCHIVED: "Conclues ou retirées",
    }

    STATUS_FILTERS = [
        ("all", "Toutes", []),
        ("available", "Disponibles", [Listing.Status.PUBLISHED]),
        (
            "reserved",
            "Réservées",
            [Listing.Status.RESERVED, Listing.Status.RESERVATION_ACCEPTED],
        ),
        ("sold", "Vendues", [Listing.Status.SOLD]),
        ("archived", "Archivée", [Listing.Status.ARCHIVED]),
    ]

    def get_queryset(self):
        reservation_qs = Reservation.objects.active().select_related("buyer")
        qs = (
            Listing.objects.filter(seller=self.request.user)
            .select_related("category")
            .prefetch_related(
                "images__image_asset", Prefetch("reservations", queryset=reservation_qs)
            )
            .order_by("-updated_at")
        )
        status_filter = self._get_status_filter()
        if status_filter:
            qs = qs.filter(status__in=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for listing in context["listings"]:
            listing.active_reservation = listing.refresh_reservation_state()
        context["reservation_expiration_hours"] = getattr(
            settings, "RESERVATION_HOLD_HOURS", 24
        )
        summary = self._build_status_summary()
        context["status_summary"] = summary
        context["status_cards"] = self._build_status_cards(summary)
        context["status_filters"] = self._build_filter_options(summary)
        context["active_filter"] = self.request.GET.get("filter", "all")
        return context

    def _build_status_summary(self):
        counts = {
            row["status"]: row["count"]
            for row in Listing.objects.filter(seller=self.request.user)
            .values("status")
            .annotate(count=Count("status"))
        }
        return counts

    def _build_status_cards(self, summary):
        cards = []
        total = sum(summary.values())
        for status in self.STATUS_ORDER:
            cards.append(
                {
                    "status": status,
                    "label": self.STATUS_LABELS.get(status, status.title()),
                    "description": self.STATUS_DESCRIPTIONS.get(status, ""),
                    "count": summary.get(status, 0),
                    "ratio": f"{int(summary.get(status, 0) / total * 100) if total else 0}%",
                }
            )
        return cards

    def _get_status_filter(self):
        filter_key = self.request.GET.get("filter", "all")
        for key, _, statuses in self.STATUS_FILTERS:
            if key == filter_key:
                return statuses
        return []

    def _build_filter_options(self, summary):
        total = sum(summary.values())
        options = []
        for key, label, statuses in self.STATUS_FILTERS:
            count = (
                sum(summary.get(status, 0) for status in statuses)
                if statuses
                else total
            )
            options.append(
                {"key": key, "label": label, "count": count},
            )
        return options


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
        return HttpResponseRedirect(
            reverse("listing_submit", kwargs={"pk": listing.id})
        )


class PhotoUploadView(LoginRequiredMixin, FormView):
    template_name = "sell/upload_photos.html"
    form_class = PhotoUploadForm

    def dispatch(self, request, *args, **kwargs):
        self.listing = get_object_or_404(Listing, id=kwargs["pk"], seller=request.user)
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_ia_count"] = DetectedItem.objects.filter(
            status=DetectedItem.Status.USER_APPROVED
        ).count()
        context["admin_swipe_url"] = reverse("ingestion:admin_swipe")
        return context


class ReservationCancelView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(
            Listing, id=kwargs["listing_id"], seller=request.user
        )
        detail_url = get_listing_detail_url(listing)
        reservation = listing.refresh_reservation_state()
        if not reservation:
            django_messages.info(request, "Il n’y a plus de réservation active.")
            return redirect(detail_url)
        reservation.cancel()
        if listing.status in {
            Listing.Status.RESERVED,
            Listing.Status.RESERVATION_ACCEPTED,
        }:
            listing.status = Listing.Status.PUBLISHED
            listing.reserved_for = None
            listing.reserved_at = None
            listing.reservation_note = ""
            listing.save(
                update_fields=[
                    "status",
                    "reserved_for",
                    "reserved_at",
                    "reservation_note",
                ]
            )
            ReservationLog.objects.create(
                listing=listing,
                user=request.user,
                action=ReservationLog.Action.CANCELLED,
                note="Annulation manuelle",
            )
        django_messages.success(request, "La réservation a été annulée.")
        return redirect(detail_url)


class ReservationAcceptView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(
            Listing, id=kwargs["listing_id"], seller=request.user
        )
        detail_url = get_listing_detail_url(listing)
        reservation = listing.refresh_reservation_state()
        if not reservation:
            django_messages.info(request, "Il n’y a plus de réservation active.")
            return redirect(detail_url)
        if listing.status not in {Listing.Status.RESERVED}:
            django_messages.info(
                request, "La réservation a déjà été validée ou le statut a changé."
            )
            return redirect(detail_url)
        listing.status = Listing.Status.RESERVATION_ACCEPTED
        listing.save(update_fields=["status"])
        django_messages.success(
            request,
            "La réservation a été acceptée et l’objet passe en statut Réservation acceptée.",
        )
        ReservationLog.objects.create(
            listing=listing,
            user=request.user,
            action=ReservationLog.Action.ACCEPTED,
            note="Acceptation manuelle.",
        )
        return redirect(detail_url)


class ListingActionView(LoginRequiredMixin, View):
    target_status = None
    success_message = ""

    def post(self, request, *args, **kwargs):
        listing = get_object_or_404(
            Listing, id=kwargs["listing_id"], seller=request.user
        )
        if not self.target_status:
            return redirect(get_listing_detail_url(listing))
        listing.status = self.target_status
        listing.save(update_fields=["status", "updated_at"])
        django_messages.success(request, self.success_message)
        return redirect(get_listing_detail_url(listing))


class ListingMarkSoldView(ListingActionView):
    target_status = Listing.Status.SOLD
    success_message = "Annonce marquée comme vendue."


class ListingArchiveView(ListingActionView):
    target_status = Listing.Status.ARCHIVED
    success_message = "Annonce archivée."


class ListingUnarchiveView(ListingActionView):
    target_status = Listing.Status.PUBLISHED
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


class ListingReminderCreateView(LoginRequiredMixin, View):
    def post(self, request, listing_id, *args, **kwargs):
        listing = get_object_or_404(Listing, id=listing_id)
        reminder, created = ListingReminder.objects.get_or_create(
            user=request.user, listing=listing
        )
        if created:
            self._notify_seller(listing, request.user)
            django_messages.success(
                request, "Nous vous préviendrons dès que l’annonce sera disponible."
            )
        else:
            django_messages.info(
                request, "Vous êtes déjà inscrit pour être prévenu."
            )
        return HttpResponseRedirect(get_listing_detail_url(listing))

    def _notify_seller(self, listing, requester):
        if not listing.seller.email:
            return
        subject = (
            f"Un acheteur veut être prévenu pour {listing.title or 'votre annonce'}"
        )
        sender = getattr(settings, "DEFAULT_FROM_EMAIL", settings.SERVER_EMAIL)
        message = "\n".join(
            [
                f"{requester.get_full_name() or requester.email} souhaite être notifié.",
                f"Annonce : {listing.title}",
                f"ID : {listing.id}",
                f"Disponible à partir de : {listing.available_from or 'à confirmer'}",
            ]
        )
        send_mail(subject, message, sender, [listing.seller.email], fail_silently=True)

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
