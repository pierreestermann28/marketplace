from django.urls import path

from .views import ProfileDetailView

app_name = "accounts"

urlpatterns = [
    path("profiles/<slug:username>/", ProfileDetailView.as_view(), name="profile_detail"),
]
