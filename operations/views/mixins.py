from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from listings.models import Listing
from operations.services import handle_review_action


class ReviewActionMixin:
    def _handle_review_action(self, request):
        action = request.POST.get("action")
        listing_id = request.POST.get("listing_id")
        listing = get_object_or_404(Listing, pk=listing_id)
        note = request.POST.get("note", "").strip()
        message, success = handle_review_action(
            action=action, listing=listing, admin_user=request.user, note=note
        )
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect(self._return_url())

    def _return_url(self):
        return reverse("operations:dashboard")
