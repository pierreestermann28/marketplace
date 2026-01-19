from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, TemplateView
from django.views import View

import stripe

from billing.entitlements import get_user_entitlement
from .forms import SignUpForm

from .models import ReputationStats, User


def _build_absolute_url(request, path):
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return request.build_absolute_uri(path)


def _user_from_metadata(metadata, email=None):
    user_id = metadata.get("user_id")
    UserModel = get_user_model()
    if user_id:
        try:
            return UserModel.objects.get(pk=int(user_id))
        except (ValueError, UserModel.DoesNotExist):
            return None
    if email:
        return UserModel.objects.filter(email=email).first()
    return None


def _apply_premium_entitlement(user, subscription_payload=None):
    entitlement = get_user_entitlement(user)
    if not entitlement:
        return
    entitlement.is_premium = True
    premium_until = None
    if subscription_payload:
        period_end = subscription_payload.get("current_period_end")
        if period_end:
            premium_until = timezone.datetime.fromtimestamp(period_end, tz=timezone.utc)
    entitlement.premium_until = premium_until
    entitlement.save(update_fields=["is_premium", "premium_until"])


def _revoke_premium_entitlement(user):
    entitlement = get_user_entitlement(user)
    if not entitlement:
        return
    entitlement.is_premium = False
    entitlement.premium_until = None
    entitlement.save(update_fields=["is_premium", "premium_until"])


class PersonalProfileView(TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        stats = getattr(user, "reputation", None)
        if not stats:
            stats = ReputationStats.for_user(user)
        context.update(
            {
                "object": user,
                "reputation_stats": stats,
                "reviews_received": user.reviews_received.select_related(
                    "order__listing"
                ).order_by("-created_at")[:5],
            }
        )
        return context


class PublicProfileView(DetailView):
    model = User
    template_name = "accounts/public_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        stats = getattr(user, "reputation", None)
        if not stats:
            stats = ReputationStats.for_user(user)
        context["reputation_stats"] = stats
        context["reviews_received"] = user.reviews_received.select_related(
            "order__listing"
        ).order_by("-created_at")[:5]
        return context


class SignUpView(FormView):
    template_name = "registration/register.html"
    form_class = SignUpForm
    success_url = reverse_lazy("onboarding")

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, "Bienvenue ! Ton compte a été créé.")
        login(self.request, user)
        return super().form_valid(form)


class PricingView(TemplateView):
    template_name = "accounts/pricing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_meta"] = {
            "title": "Swipe2Sell Premium",
            "description": "Débloquez des quotas illimités et une surveillance premium.",
        }
        context["stripe_publishable_key"] = settings.STRIPE_PUBLISHABLE_KEY
        context["checkout_url"] = reverse_lazy("accounts:stripe_checkout_session")
        context["price_id"] = settings.STRIPE_PREMIUM_PRICE_ID
        return context


class StripeCheckoutSessionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        price_id = settings.STRIPE_PREMIUM_PRICE_ID
        secret = settings.STRIPE_SECRET_KEY
        if not price_id or not secret:
            return JsonResponse({"error": "Stripe non configuré"}, status=503)
        stripe.api_key = secret
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                customer_email=request.user.email,
                allow_promotion_codes=True,
                subscription_data={
                    "metadata": {"user_id": str(request.user.pk)},
                },
                metadata={"user_id": str(request.user.pk)},
                success_url=_build_absolute_url(
                    request, settings.STRIPE_CHECKOUT_SUCCESS_URL
                ),
                cancel_url=_build_absolute_url(
                    request, settings.STRIPE_CHECKOUT_CANCEL_URL
                ),
            )
        except stripe.error.StripeError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
        return JsonResponse({"id": session.id})


@csrf_exempt
@require_POST
def stripe_webhook(request):
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        return HttpResponse(status=404)
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    stripe.api_key = settings.STRIPE_SECRET_KEY or ""
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    data = event.get("data", {}).get("object", {}) or {}
    metadata = data.get("metadata", {})
    user = _user_from_metadata(metadata, email=data.get("customer_email"))

    if event["type"] == "checkout.session.completed":
        subscription_id = data.get("subscription")
        subscription_payload = {}
        if subscription_id:
            try:
                subscription_payload = stripe.Subscription.retrieve(subscription_id)
            except stripe.error.StripeError:
                subscription_payload = {}
        if user:
            _apply_premium_entitlement(user, subscription_payload)
    elif event["type"] in {
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        subscription_payload = data
        if user:
            status = subscription_payload.get("status")
            if status in {"active", "trialing"}:
                _apply_premium_entitlement(user, subscription_payload)
            else:
                _revoke_premium_entitlement(user)
    return HttpResponse(status=200)
