from django.urls import include, path

from .views import ProfileDetailView, SignUpView

app_name = "accounts"

urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    path("profiles/<slug:username>/", ProfileDetailView.as_view(), name="profile_detail"),
    path("register/", SignUpView.as_view(), name="register"),
]
