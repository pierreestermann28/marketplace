from collections import Counter
from typing import List, Tuple

from catalog.models import Category
from location.models import City as LocationCity

from .models import Favorite, Listing, ListingView, Reservation, SearchAlert


class ListingRecommendationEngine:
    MAX_CANDIDATES = 300
    FAVORITE_CATEGORY_WEIGHT = 2.0
    RESERVATION_CATEGORY_WEIGHT = 1.5
    ALERT_CATEGORY_WEIGHT = 1.2
    ALERT_CITY_WEIGHT = 1.1
    ALERT_KEYWORD_WEIGHT = 1.0
    FAVORITE_LISTING_DEBOOST = -0.8
    VIEWED_LISTING_DEBOOST = -0.3

    def __init__(self, user):
        self.user = user
        self.category_scores = Counter()
        self.city_scores = Counter()
        self.alert_keywords = []
        self.favorite_listing_ids = set()
        self.viewed_listing_ids = set()
        self._collect_signals()

    def recommend(self, limit=6) -> Tuple[List[int], str]:
        if not self.user.is_authenticated:
            return [], "Suggestions personnalisées"

        candidates = self._candidate_queryset()
        scored = []
        for listing in candidates:
            score = self._score_listing(listing)
            scored.append((score, listing.id))

        if not scored:
            return [], "Suggestions personnalisées"

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = []
        seen = set()
        for _, listing_id in scored:
            if listing_id in seen:
                continue
            seen.add(listing_id)
            selected.append(listing_id)
            if len(selected) >= limit:
                break

        reason = self._build_reason()
        return selected, reason

    def _collect_signals(self):
        if not self.user.is_authenticated:
            return

        self._collect_favorite_signals()
        self._collect_reservation_signals()
        self._collect_alert_signals()
        self._collect_view_signals()

    def _collect_favorite_signals(self):
        favorites = (
            Favorite.objects.filter(user=self.user)
            .select_related("listing__category")
        )
        self.favorite_listing_ids = {
            favorite.listing_id for favorite in favorites if favorite.listing_id
        }
        category_slugs = [
            favorite.listing.category.slug
            for favorite in favorites
            if favorite.listing and favorite.listing.category
        ]
        counts = Counter(category_slugs)
        for slug, count in counts.items():
            self.category_scores[slug] += count * self.FAVORITE_CATEGORY_WEIGHT

    def _collect_reservation_signals(self):
        reservations = (
            Reservation.objects.filter(
                buyer=self.user, cancelled_at__isnull=True
            )
            .select_related("listing__category")
        )
        category_slugs = [
            reservation.listing.category.slug
            for reservation in reservations
            if reservation.listing and reservation.listing.category
        ]
        counts = Counter(category_slugs)
        for slug, count in counts.items():
            self.category_scores[slug] += count * self.RESERVATION_CATEGORY_WEIGHT

    def _collect_alert_signals(self):
        alerts = SearchAlert.objects.filter(user=self.user, is_active=True).select_related(
            "category",
            "location_city",
        )
        for alert in alerts:
            if alert.category and alert.category.slug:
                self.category_scores[alert.category.slug] += self.ALERT_CATEGORY_WEIGHT
            if alert.location_city and alert.location_city.slug:
                self.city_scores[alert.location_city.slug] += self.ALERT_CITY_WEIGHT
            keyword = (alert.keyword or "").strip().lower()
            if keyword:
                self.alert_keywords.append(keyword)

    def _collect_view_signals(self):
        viewed_ids = (
            ListingView.objects.filter(user=self.user)
            .order_by("-viewed_at")
            .values_list("listing_id", flat=True)[:200]
        )
        self.viewed_listing_ids = set(viewed_ids)

    def _candidate_queryset(self):
        return list(
            Listing.objects.filter(status=Listing.Status.PUBLISHED)
            .select_related("category", "location_city")
            .order_by("-created_at")[: self.MAX_CANDIDATES]
        )

    def _score_listing(self, listing: Listing) -> float:
        score = 0.05
        category_slug = listing.category.slug if listing.category else None
        if category_slug:
            score += self.category_scores.get(category_slug, 0)
        city_slug = listing.location_city.slug if listing.location_city else None
        if city_slug:
            score += self.city_scores.get(city_slug, 0)
        text = f"{listing.title or ''} {listing.description or ''}".lower()
        for keyword in self.alert_keywords:
            if keyword in text:
                score += self.ALERT_KEYWORD_WEIGHT
                break
        if listing.id in self.favorite_listing_ids:
            score += self.FAVORITE_LISTING_DEBOOST
        if listing.id in self.viewed_listing_ids:
            score += self.VIEWED_LISTING_DEBOOST
        return score

    def _build_reason(self) -> str:
        if self.category_scores:
            top = max(self.category_scores, key=self.category_scores.get)
            category = Category.objects.filter(slug=top).first()
            if category:
                return f"vos favoris dans {category.name}"
            return "vos favoris"
        if self.city_scores:
            top = max(self.city_scores, key=self.city_scores.get)
            city = LocationCity.objects.filter(slug=top).first()
            if city:
                return f"Alertes actives à {city.name}"
            return "Alertes actives"
        if self.alert_keywords:
            return "Alertes personnalisées"
        return "Suggestions personnalisées"
