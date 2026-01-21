from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Exists, OuterRef, Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, ListView

from catalog.models import Category
from catalog.services import get_categories_with_listings, list_categories
from commerce.models import Review
from location.models import City as LocationCity

from listings.models import (
    Favorite,
    Listing,
    ListingImage,
    ListingReminder,
    ListingView,
)
from listings.queries.listing_detail import build_listing_detail_queryset
from listings.queries.listing_feed import (
    build_filters_from_params,
    build_home_feed_queryset,
    get_selected_category_slugs,
    get_selected_city_ids,
    resolve_selected_categories,
    resolve_selected_cities,
)
from listings.queries.my_listings import (
    get_listing_status_counts,
    get_my_listings_queryset,
)
from listings.services import record_listing_view
from listings.services.images import get_primary_image
from listings.services.recommendations import ListingRecommendationEngine
from reports.forms import ReportForm
from listings.utils import user_can_view_contact_info


def get_listing_detail_url(listing):
    slug = listing.slug or "item"
    return reverse("listing_detail", kwargs={"slug": slug, "uuid": listing.id})


class HomeFeedView(ListView):
    model = Listing
    template_name = "pages/home.html"
    context_object_name = "listings"
    paginate_by = 24
    status_filter = [Listing.Status.PUBLISHED]
    default_title = "Annonces responsables | Swipe2Sell"
    default_description = "Vendez et achetez localement avec Swipe2Sell : annonces vérifiées, échanges sécurisés et durabilité."

    def get_queryset(self):
        filters = build_filters_from_params(self.request.GET)
        return build_home_feed_queryset(filters, self.request.user, self.status_filter)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = list_categories(order_by=["name"])
        filters = build_filters_from_params(self.request.GET)
        selected_city_ids = get_selected_city_ids(self.request.GET)
        category_slugs = get_selected_category_slugs(self.request.GET)
        context["filters"] = {
            **filters,
            "querystring": self._get_filter_querystring(),
        }
        context["selected_categories"] = resolve_selected_categories(category_slugs)
        context["selected_cities"] = resolve_selected_cities(selected_city_ids)
        recommended, reason = self._get_recommendations()
        context["recommended_listings"] = recommended
        context["recommendation_reason"] = reason
        context["feed_partial_url"] = self._build_feed_partial_url(
            context["filters"]["querystring"]
        )
        context["featured_categories"] = (
            get_categories_with_listings(self.status_filter)
            .annotate(count=Count("listings"))
            .order_by("-count")[:6]
        )
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
        engine = ListingRecommendationEngine(self.request.user)
        recommendation = engine.recommend(limit=6)
        recommended_ids = recommendation.listing_ids
        reason = recommendation.reason
        if not recommended_ids:
            return [], reason
        image_qs = self._image_prefetch_queryset()
        qs = (
            Listing.objects.filter(id__in=recommended_ids)
            .select_related("category", "seller")
            .prefetch_related(Prefetch("images", queryset=image_qs))
        )
        listings_by_id = {listing.id: listing for listing in qs}
        ordered = [
            listings_by_id[lid] for lid in recommended_ids if lid in listings_by_id
        ]
        return ordered, reason

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
        description = f"Explorez toutes les annonces {self.category.name} vérifiées sur Swipe2Sell."
        context["page_heading"] = f"Catégorie {self.category.name}"
        context["page_description"] = description
        context["page_meta"] = {
            "title": f"{self.category.name} | Swipe2Sell",
            "description": description,
            "og_title": f"{self.category.name} – Swipe2Sell",
            "og_description": description,
            "og_type": "website",
        }
        return context


class CityListingView(HomeFeedView):
    template_name = "pages/listings_feed.html"

    def dispatch(self, request, *args, **kwargs):
        self.location_city = get_object_or_404(LocationCity, slug=kwargs["slug"])
        self.city_label = self.location_city.name
        query_params = request.GET.copy()
        query_params["city"] = self.city_label
        query_params["city_slug"] = self.location_city.slug
        query_params.setlist("city_ids", [str(self.location_city.id)])
        request.GET = query_params
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        description = f"Les meilleures annonces disponibles à {self.city_label}."
        context["page_heading"] = f"{self.city_label}"
        context["page_description"] = description
        context["page_meta"] = {
            "title": f"Annonces à {self.city_label} | Swipe2Sell",
            "description": description,
            "og_title": f"Annonces à {self.city_label}",
            "og_description": description,
            "og_type": "website",
        }
        return context


class SuggestionFeedView(HomeFeedView):
    template_name = "pages/suggestions.html"


class ListingDetailView(DetailView):
    model = Listing
    template_name = "pages/listing_detail.html"
    context_object_name = "listing"

    def get_queryset(self):
        return build_listing_detail_queryset(self.request.user)

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
        record_listing_view(listing=listing, user=self.request.user)
        primary_image = get_primary_image(listing=listing)
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
                    reverse("listing_remind", kwargs={"listing_id": listing.id})
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
                "report_form": ReportForm(),
                "report_action_url": reverse(
                    "reports:listing_report", kwargs={"listing_id": listing.id}
                ),
            }
        )
        context["page_meta"] = {
            "title": f"{listing.title} | Swipe2Sell",
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
        buyer_reviews = seller.reviews_received.filter(role=Review.Role.SELLER_TO_BUYER)
        seller_avg = seller_reviews.aggregate(avg=Avg("rating"))["avg"]
        buyer_avg = buyer_reviews.aggregate(avg=Avg("rating"))["avg"]
        return {
            "seller_rating_avg": seller_avg or 0,
            "seller_rating_count": seller_reviews.count(),
            "items_sold_count": seller_reviews.count(),
            "buyer_rating_avg": buyer_avg or 0,
            "buyer_rating_count": buyer_reviews.count(),
        }


class MyListingsView(LoginRequiredMixin, ListView):
    model = Listing
    template_name = "sell/my_listings.html"
    context_object_name = "listings"

    STATUS_ORDER = [
        Listing.Status.DRAFT,
        Listing.Status.PENDING_REVIEW,
        Listing.Status.PUBLISHED,
        Listing.Status.SOLD,
        Listing.Status.REJECTED,
        Listing.Status.ARCHIVED,
    ]

    STATUS_LABELS = {
        Listing.Status.DRAFT: "Brouillons",
        Listing.Status.PENDING_REVIEW: "En relecture",
        Listing.Status.PUBLISHED: "Publiés",
        Listing.Status.SOLD: "Vendues",
        Listing.Status.REJECTED: "Refusés",
        Listing.Status.ARCHIVED: "Archivée",
    }

    STATUS_DESCRIPTIONS = {
        Listing.Status.DRAFT: "Complète les infos",
        Listing.Status.PENDING_REVIEW: "Sous validation équipe",
        Listing.Status.PUBLISHED: "Visibles par tous",
        Listing.Status.SOLD: "Livrées ou payées",
        Listing.Status.REJECTED: "Demande une mise à jour",
        Listing.Status.ARCHIVED: "Conclues ou retirées",
    }

    STATUS_FILTERS = [
        ("all", "Toutes", []),
        ("available", "Disponibles", [Listing.Status.PUBLISHED]),
        ("sold", "Vendues", [Listing.Status.SOLD]),
        ("archived", "Archivée", [Listing.Status.ARCHIVED]),
    ]

    def get_queryset(self):
        return get_my_listings_queryset(
            user=self.request.user, status_filter=self._get_status_filter()
        )

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

        context["public_visible_statuses"] = [
            Listing.Status.PUBLISHED,
        ]
        return context

    def _build_status_summary(self):
        return get_listing_status_counts(self.request.user)

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
