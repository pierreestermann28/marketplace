from django.urls import path

from .views import (
    AdminSwipeFragmentView,
    AdminSwipeView,
    BatchProcessingView,
    BatchStatusFragmentView,
    BatchSwipeView,
    BatchUploadCreateView,
    DetectedItemAdminApproveView,
    DetectedItemAdminRejectView,
    DetectedItemApproveView,
    DetectedItemRejectView,
)

app_name = "ingestion"

urlpatterns = [
    path("create/", BatchUploadCreateView.as_view(), name="batch_upload"),
    path(
        "<uuid:batch_id>/processing/",
        BatchProcessingView.as_view(),
        name="batch_processing",
    ),
    path(
        "<uuid:batch_id>/processing/status/",
        BatchStatusFragmentView.as_view(),
        name="batch_status_fragment",
    ),
    path(
        "<uuid:batch_id>/swipe/",
        BatchSwipeView.as_view(),
        name="batch_swipe",
    ),
    path(
        "items/<int:item_id>/approve/",
        DetectedItemApproveView.as_view(),
        name="detecteditem_approve",
    ),
    path(
        "items/<int:item_id>/reject/",
        DetectedItemRejectView.as_view(),
        name="detecteditem_reject",
    ),
    path(
        "admin/swipe/",
        AdminSwipeView.as_view(),
        name="admin_swipe",
    ),
    path(
        "admin/swipe/card/",
        AdminSwipeFragmentView.as_view(),
        name="admin_swipe_fragment",
    ),
    path(
        "admin/items/<int:item_id>/approve/",
        DetectedItemAdminApproveView.as_view(),
        name="detecteditem_admin_approve",
    ),
    path(
        "admin/items/<int:item_id>/reject/",
        DetectedItemAdminRejectView.as_view(),
        name="detecteditem_admin_reject",
    ),
]
