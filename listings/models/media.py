from django.conf import settings
from django.db import models
from django.utils import timezone


class ListingImage(models.Model):
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="images"
    )
    image_asset = models.ForeignKey(
        "mediahub.ImageAsset", on_delete=models.PROTECT, related_name="listing_images"
    )
    keyframe = models.ForeignKey(
        "mediahub.Keyframe",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listing_images",
    )

    is_primary = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["listing", "sort_order"])]
