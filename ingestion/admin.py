# ingestion/admin.py
from django.contrib import admin
from .models import DetectedItem


@admin.register(DetectedItem)
class DetectedItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "batch",
        "status",
        "title_suggested",
        "listing",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("title_suggested", "category_suggested", "listing__title")
    autocomplete_fields = ("owner", "batch", "hero_asset", "listing")
