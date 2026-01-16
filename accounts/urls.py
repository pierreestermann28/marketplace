from django.urls import include, path

from .views import (
    PersonalProfileView,
    PublicProfileView,
    SignUpView,
    PricingView,
    StripeCheckoutSessionView,
    stripe_webhook,
)

app_name = "accounts"

urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    path("profile/", PersonalProfileView.as_view(), name="personal_profile"),
    path("profiles/<int:pk>/", PublicProfileView.as_view(), name="public_profile"),
    path("register/", SignUpView.as_view(), name="register"),
    path("pricing/", PricingView.as_view(), name="pricing"),
    path("billing/checkout/", StripeCheckoutSessionView.as_view(), name="stripe_checkout_session"),
    path("billing/webhook/", stripe_webhook, name="stripe_webhook"),
]
