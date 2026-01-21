import uuid

from django.conf import settings
from django.db import models


class ImageAsset(models.Model):
    class Source(models.TextChoices):
        UPLOAD = "upload", "Upload"
        KEYFRAME = "keyframe", "Keyframe"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="image_assets",
    )

    image = models.ImageField(upload_to="images/%Y/%m/%d/")
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.UPLOAD
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["source", "created_at"]),
        ]
