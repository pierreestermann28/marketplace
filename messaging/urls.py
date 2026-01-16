from django.urls import path

from .views import (
    ConversationDashboardView,
    ConversationDetailView,
    ConversationStartView,
    SellerReservationCreateView,
)

app_name = "messages"

urlpatterns = [
    path("", ConversationDashboardView.as_view(), name="list"),
    path("start/<uuid:listing_id>/", ConversationStartView.as_view(), name="start"),
    path("reserve/<int:pk>/", SellerReservationCreateView.as_view(), name="reserve"),
    path("<int:pk>/", ConversationDetailView.as_view(), name="detail"),
]
