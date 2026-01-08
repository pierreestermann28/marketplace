from django.contrib import admin
from django.utils import timezone

from .models import Listing


@admin.action(description="Approve selected listings")
def approve_listings(modeladmin, request, queryset):
    queryset.update(
        status=Listing.Status.PUBLISHED,
        moderated_by=request.user,
        moderated_at=timezone.now(),
    )


@admin.action(description="Reject selected listings")
def reject_listings(modeladmin, request, queryset):
    queryset.update(
        status=Listing.Status.REJECTED,
        moderated_by=request.user,
        moderated_at=timezone.now(),
    )


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "price_cents", "currency", "status")
    list_filter = ("status",)
    search_fields = ("title", "seller__username", "seller__email")
    actions = (approve_listings, reject_listings)
