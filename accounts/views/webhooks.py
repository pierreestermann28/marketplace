from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import stripe

from accounts.services import (
    StripeConfigurationError,
    handle_stripe_event,
    parse_stripe_event,
)


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
