from django.urls import path

from .views import OperationsDashboardView

app_name = "operations"

urlpatterns = [
    path("staff/operations/", OperationsDashboardView.as_view(), name="dashboard"),
]
