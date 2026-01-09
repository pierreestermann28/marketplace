from django.contrib import admin
from django.utils.html import format_html

from .models import ImageAsset, Keyframe, VideoUpload


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

# Register your models here.
