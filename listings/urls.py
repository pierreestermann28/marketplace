from django.urls import path

from .views import (
    HomeFeedView,
    ListingDetailView,
    ListingFavoriteToggleView,
    ListingStartView,
    ListingModerationDetailView,
    MyListingsView,
    PhotoUploadView,
    ReservationCancelView,
    ReservationCreateView,
    ReviewQueueView,
    SubmitForReviewView,
)

urlpatterns = [
    path("", HomeFeedView.as_view(), name="home"),
    path("items/<uuid:listing_id>/favorite/", ListingFavoriteToggleView.as_view(), name="listing_favorite"),
    path("items/<uuid:listing_id>/reserve/", ReservationCreateView.as_view(), name="listing_reserve"),
    path("items/<uuid:listing_id>/cancel-reservation/", ReservationCancelView.as_view(), name="listing_cancel_reservation"),
    path("items/<slug:slug>-<uuid:uuid>/", ListingDetailView.as_view(), name="listing_detail"),
    path("my/listings/", MyListingsView.as_view(), name="my_listings"),
    path("sell/create/", ListingStartView.as_view(), name="listing_create"),
    path("sell/<uuid:pk>/photos/", PhotoUploadView.as_view(), name="listing_photos"),
    path("sell/<uuid:pk>/submit/", SubmitForReviewView.as_view(), name="listing_submit"),
    path("staff/review-queue/", ReviewQueueView.as_view(), name="review_queue"),
    path(
        "staff/review-queue/<uuid:pk>/",
        ListingModerationDetailView.as_view(),
        name="review_listing",
    ),
]
