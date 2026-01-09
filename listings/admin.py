from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Listing, ListingImage


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
    search_fields = ("title", "seller__email")
    actions = (approve_listings, reject_listings)


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0
    readonly_fields = ("preview",)
    fields = ("preview", "image_asset", "is_primary", "sort_order")

    def preview(self, obj):
        if obj.image_asset and obj.image_asset.image:
            return format_html(
                '<img src="{}" style="height:60px;width:auto;border-radius:6px;" />',
                obj.image_asset.image.url,
            )
        return "-"

    preview.short_description = "Preview"


ListingAdmin.inlines = [ListingImageInline]
