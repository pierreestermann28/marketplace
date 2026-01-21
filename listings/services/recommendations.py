# listings/services/recommendations.py
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from django.db.models import QuerySet

from catalog.services import find_category_by_slug_or_name
from commerce.models import Order
from listings.models import Favorite, Listing, ListingView, SearchAlert
from location.models import City as LocationCity


@dataclass(frozen=True)
class RecommendationResult:
    listing_ids: List[
        str
    ]  # UUIDs (str) or uuid.UUID, depending on your Listing.pk type
    reason: str


class ListingRecommendationEngine:
    """
    Lightweight on-demand recommender based on user signals:
    - favorites
    - past orders ("purchases")
    - search alerts (category/city/keyword)
    - viewed listings (deboost)

    No async required, just score the most recent candidates.
    """

    MAX_CANDIDATES = 300

    FAVORITE_CATEGORY_WEIGHT = 2.0
    ORDER_CATEGORY_WEIGHT = 1.5

    ALERT_CATEGORY_WEIGHT = 1.2
    ALERT_CITY_WEIGHT = 1.1
    ALERT_KEYWORD_WEIGHT = 1.0

    FAVORITE_LISTING_DEBOOST = -0.8
    VIEWED_LISTING_DEBOOST = -0.3

    BASE_SCORE = 0.05

    def __init__(self, user):
        self.user = user

        self.category_scores: Counter[str] = Counter()
        self.city_scores: Counter[str] = Counter()  # key: city_id as str
        self.alert_keywords: list[str] = []

        self.favorite_listing_ids: set = set()
        self.viewed_listing_ids: set = set()

        self._collect_signals()

    def recommend(self, limit: int = 6) -> RecommendationResult:
        if not getattr(self.user, "is_authenticated", False):
            return RecommendationResult([], "Suggestions personnalisées")

        candidates = self._candidate_queryset()
        scored: list[tuple[float, str]] = []

        for listing in candidates:
            score = self._score_listing(listing)
            scored.append((score, str(listing.id)))

        if not scored:
            return RecommendationResult([], "Suggestions personnalisées")

        scored.sort(key=lambda x: x[0], reverse=True)

        selected: list[str] = []
        seen: set[str] = set()
        for _score, listing_id in scored:
            if listing_id in seen:
                continue
            seen.add(listing_id)
            selected.append(listing_id)
            if len(selected) >= limit:
                break

        return RecommendationResult(selected, self._build_reason())

    # -------------------------
    # Signals collection
    # -------------------------

    def _collect_signals(self) -> None:
        self._collect_favorite_signals()
        self._collect_order_signals()
        self._collect_alert_signals()
        self._collect_view_signals()

    def _collect_favorite_signals(self) -> None:
        favorites = Favorite.objects.filter(user=self.user).select_related(
            "listing__category"
        )

        self.favorite_listing_ids = {
            fav.listing_id for fav in favorites if fav.listing_id
        }

        category_slugs = [
            fav.listing.category.slug
            for fav in favorites
            if fav.listing and fav.listing.category and fav.listing.category.slug
        ]

        counts = Counter(category_slugs)
        for slug, count in counts.items():
            self.category_scores[slug] += count * self.FAVORITE_CATEGORY_WEIGHT

    def _collect_order_signals(self) -> None:
        """
        V2: no in-app payment, but you still have Order/Offer-like object.
        We use completed orders as a “preference signal”.
        """
        orders = (
            Order.objects.filter(buyer=self.user)
            .select_related("listing__category")
            .only("id", "listing_id", "listing__category__slug", "status")
        )

        # Option: only completed orders (recommended)
        # If you want more signals, include other statuses
        orders = orders.filter(status=Order.Status.COMPLETED)

        category_slugs = [
            o.listing.category.slug
            for o in orders
            if o.listing and o.listing.category and o.listing.category.slug
        ]

        counts = Counter(category_slugs)
        for slug, count in counts.items():
            self.category_scores[slug] += count * self.ORDER_CATEGORY_WEIGHT

    def _collect_alert_signals(self) -> None:
        alerts = SearchAlert.objects.filter(
            user=self.user, is_active=True
        ).select_related("category", "location_city")

        for alert in alerts:
            if alert.category and alert.category.slug:
                self.category_scores[alert.category.slug] += self.ALERT_CATEGORY_WEIGHT

            # LocationCity in your V2 has id + name + postal_code; not sure slug exists.
            # So we score on city_id (stable) instead of slug.
            if alert.location_city_id:
                self.city_scores[str(alert.location_city_id)] += self.ALERT_CITY_WEIGHT

            keyword = (alert.keyword or "").strip().lower()
            if keyword:
                self.alert_keywords.append(keyword)

    def _collect_view_signals(self) -> None:
        viewed_ids = (
            ListingView.objects.filter(user=self.user)
            .order_by("-viewed_at")
            .values_list("listing_id", flat=True)[:200]
        )
        self.viewed_listing_ids = set(viewed_ids)

    # -------------------------
    # Candidate selection / scoring
    # -------------------------

    def _candidate_queryset(self) -> list[Listing]:
        """
        Keep it simple: score the most recent listings.
        You can evolve later: filter by categories/cities to reduce candidates.
        """
        return list(
            Listing.objects.filter(status=Listing.Status.PUBLISHED)
            .select_related("category", "location_city")
            .order_by("-created_at")[: self.MAX_CANDIDATES]
        )

    def _score_listing(self, listing: Listing) -> float:
        score = float(self.BASE_SCORE)

        category_slug = listing.category.slug if listing.category else None
        if category_slug:
            score += float(self.category_scores.get(category_slug, 0))

        if listing.location_city_id:
            score += float(self.city_scores.get(str(listing.location_city_id), 0))

        if self.alert_keywords:
            text = f"{listing.title or ''} {listing.description or ''}".lower()
            for kw in self.alert_keywords:
                if kw in text:
                    score += float(self.ALERT_KEYWORD_WEIGHT)
                    break

        if listing.id in self.favorite_listing_ids:
            score += float(self.FAVORITE_LISTING_DEBOOST)

        if listing.id in self.viewed_listing_ids:
            score += float(self.VIEWED_LISTING_DEBOOST)

        return score

    # -------------------------
    # UX reason
    # -------------------------

    def _build_reason(self) -> str:
        if self.category_scores:
            top_slug = max(self.category_scores, key=self.category_scores.get)
            category = find_category_by_slug_or_name(top_slug)
            if category:
                return f"vos favoris dans {category.name}"
            return "vos favoris"

        if self.city_scores:
            top_city_id = max(self.city_scores, key=self.city_scores.get)
            city = LocationCity.objects.filter(pk=top_city_id).only("name").first()
            if city:
                return f"Alertes actives à {city.name}"
            return "Alertes actives"

        if self.alert_keywords:
            return "Alertes personnalisées"

        return "Suggestions personnalisées"


def recommend_listing_ids_for_user(*, user, limit: int = 6) -> RecommendationResult:
    """
    Facade simple pour tes views.
    """
    engine = ListingRecommendationEngine(user)
    return engine.recommend(limit=limit)
