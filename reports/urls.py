from django.urls import path

from .views import ConversationReportCreateView, ListingReportCreateView, ReportingLandingView

app_name = "reports"

urlpatterns = [
    path("", ReportingLandingView.as_view(), name="landing"),
    path("listings/<uuid:listing_id>/report/", ListingReportCreateView.as_view(), name="listing_report"),
    path("conversations/<int:pk>/report/", ConversationReportCreateView.as_view(), name="conversation_report"),
]
