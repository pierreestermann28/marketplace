from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

import stripe

from accounts.services import (
    StripeConfigurationError,
    create_checkout_session,
)


class StripeCheckoutSessionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            session = create_checkout_session(user=request.user, request=request)
        except StripeConfigurationError:
            return JsonResponse({"error": "Stripe non configuré"}, status=503)
        except stripe.error.StripeError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
        return JsonResponse({"id": session.id})
