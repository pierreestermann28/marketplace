from django.urls import path

from .views.buyer import (
    ListingFavoriteToggleView,
    OnboardingView,
    SearchAlertCreateView,
    SearchAlertDeleteView,
)
from listings.views.htmx import HomeFeedPartialView, WishlistView
from listings.views.public import (
    CategoryListingView,
    CityListingView,
    HomeFeedView,
    ListingDetailView,
    MyListingsView,
    SuggestionFeedView,
)
from listings.views.seller import (
    ListingArchiveView,
    ListingMarkSoldView,
    ListingModerationDetailView,
    ListingReminderCreateView,
    ListingStartView,
    ListingUnarchiveView,
    PhotoUploadView,
    ReservationAcceptView,
    ReservationCancelView,
    ReviewQueueView,
    SubmitForReviewView,
)

urlpatterns = [
    path("", HomeFeedView.as_view(), name="home"),
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path(
        "items/<uuid:listing_id>/favorite/",
        ListingFavoriteToggleView.as_view(),
        name="listing_favorite",
    ),
    path(
        "items/<uuid:listing_id>/cancel-reservation/",
        ReservationCancelView.as_view(),
        name="listing_cancel_reservation",
    ),
    path(
        "items/<uuid:listing_id>/remind/",
        ListingReminderCreateView.as_view(),
        name="listing_remind",
    ),
    path("alerts/create/", SearchAlertCreateView.as_view(), name="search_alert_create"),
    path(
        "alerts/<int:pk>/delete/",
        SearchAlertDeleteView.as_view(),
        name="search_alert_delete",
    ),
    path(
        "categories/<slug:slug>/",
        CategoryListingView.as_view(),
        name="category_listings",
    ),
    path("villes/<slug:slug>/", CityListingView.as_view(), name="city_listings"),
    path(
        "items/<slug:slug>-<uuid:uuid>/",
        ListingDetailView.as_view(),
        name="listing_detail",
    ),
    path(
        "items/<uuid:listing_id>/mark-sold/",
        ListingMarkSoldView.as_view(),
        name="listing_mark_sold",
    ),
    path(
        "items/<uuid:listing_id>/archive/",
        ListingArchiveView.as_view(),
        name="listing_archive",
    ),
    path(
        "items/<uuid:listing_id>/unarchive/",
        ListingUnarchiveView.as_view(),
        name="listing_unarchive",
    ),
    path("feed/partial/", HomeFeedPartialView.as_view(), name="home_feed_partial"),
    path("my/listings/", MyListingsView.as_view(), name="my_listings"),
    path(
        "items/<uuid:listing_id>/accept-reservation/",
        ReservationAcceptView.as_view(),
        name="listing_accept_reservation",
    ),
    path("wishlist/", WishlistView.as_view(), name="wishlist"),
    path("sell/create/", ListingStartView.as_view(), name="listing_create"),
    path("sell/<uuid:pk>/photos/", PhotoUploadView.as_view(), name="listing_photos"),
    path(
        "sell/<uuid:pk>/submit/", SubmitForReviewView.as_view(), name="listing_submit"
    ),
    path("staff/review-queue/", ReviewQueueView.as_view(), name="review_queue"),
    path(
        "staff/review-queue/<uuid:pk>/",
        ListingModerationDetailView.as_view(),
        name="review_listing",
    ),
    path("suggestions/", SuggestionFeedView.as_view(), name="suggestions"),
]
