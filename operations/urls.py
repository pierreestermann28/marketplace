from django.urls import path

from .views import AdminListingModerationView, OperationsDashboardView

app_name = "operations"

urlpatterns = [
    path("staff/operations/", OperationsDashboardView.as_view(), name="dashboard"),
    path("staff/listings/", AdminListingModerationView.as_view(), name="admin_listings"),
]
