"""View package for the ingestion app."""

from .actions import DetectedItemApproveView, DetectedItemRejectView
from .admin import (
    AdminSwipeFragmentView,
    AdminSwipeView,
    DetectedItemAdminApproveView,
    DetectedItemAdminRejectView,
)
from .batches import (
    BatchProcessingRetryView,
    BatchProcessingView,
    BatchStatusFragmentView,
    BatchSwipeView,
    BatchUploadCreateView,
)
from .swipe import SwipeDecisionView, SwipeListView
from .htmx import SwipeNextCardView

__all__ = [
    "BatchUploadCreateView",
    "BatchProcessingView",
    "BatchStatusFragmentView",
    "BatchProcessingRetryView",
    "BatchSwipeView",
    "DetectedItemApproveView",
    "DetectedItemRejectView",
    "AdminSwipeView",
    "AdminSwipeFragmentView",
    "DetectedItemAdminApproveView",
    "DetectedItemAdminRejectView",
    "SwipeListView",
    "SwipeNextCardView",
    "SwipeDecisionView",
]
