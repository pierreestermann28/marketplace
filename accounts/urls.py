from django.urls import include, path

from .views import PersonalProfileView, PublicProfileView, SignUpView

app_name = "accounts"

urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    path("profile/", PersonalProfileView.as_view(), name="personal_profile"),
    path("profiles/<int:pk>/", PublicProfileView.as_view(), name="public_profile"),
    path("register/", SignUpView.as_view(), name="register"),
]
