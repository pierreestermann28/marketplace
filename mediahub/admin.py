from django.contrib import admin
from django.utils.html import format_html

from .models import BatchUpload, ImageAsset, Keyframe, MediaAsset, VideoUpload


@admin.register(ImageAsset)
class ImageAssetAdmin(admin.ModelAdmin):
    list_display = ("preview", "user", "created_at")
    readonly_fields = ("preview",)
    search_fields = ("user__email",)
    list_filter = ("created_at",)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:80px;height:auto;border-radius:8px;" />',
                obj.image.url,
            )
        return "-"

    preview.short_description = "Preview"


@admin.register(VideoUpload)
class VideoUploadAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "created_at")


@admin.register(Keyframe)
class KeyframeAdmin(admin.ModelAdmin):
    list_display = ("video", "timestamp_ms", "is_selected")


@admin.register(BatchUpload)
class BatchUploadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "status",
        "media_count",
        "processing_started_at",
        "processed_at",
        "created_at",
    )
    list_filter = ("status", "created_at", "owner")
    search_fields = ("owner__email",)
    readonly_fields = ("processing_started_at", "processed_at", "created_at")


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("id", "media_type", "batch", "image_asset", "created_at")
    list_filter = ("media_type", "source", "batch__status")
    search_fields = ("batch__owner__email", "image_asset__user__email")

# Register your models here.
