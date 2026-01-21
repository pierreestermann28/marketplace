from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, TemplateView
from django.views import View

import stripe

from .forms import SignUpForm
from .models import ReputationStats, User
from .services import (
    StripeConfigurationError,
    create_checkout_session,
    handle_stripe_event,
    parse_stripe_event,
)




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
        try:
            session = create_checkout_session(user=request.user, request=request)
        except StripeConfigurationError:
            return JsonResponse({"error": "Stripe non configuré"}, status=503)
        except stripe.error.StripeError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
        return JsonResponse({"id": session.id})


@csrf_exempt
@require_POST
def stripe_webhook(request):
    try:
        event = parse_stripe_event(request)
    except StripeConfigurationError:
        return HttpResponse(status=404)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    handle_stripe_event(event)
    return HttpResponse(status=200)
