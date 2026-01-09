from django.urls import path

from .views import ReviewCreateView

app_name = "commerce"

urlpatterns = [
    path(
        "orders/<uuid:order_id>/review/<str:role>/",
        ReviewCreateView.as_view(),
        name="order_review",
    ),
]
