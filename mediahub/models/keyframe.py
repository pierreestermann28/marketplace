import uuid

from django.db import models


class Keyframe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    video = models.ForeignKey(
        "mediahub.VideoUpload",
        on_delete=models.CASCADE,
        related_name="keyframes",
    )

    image = models.ImageField(upload_to="keyframes/%Y/%m/%d/")
    timestamp_ms = models.PositiveIntegerField(db_index=True)

    sharpness_score = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    is_selected = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["video", "timestamp_ms"],
                name="uniq_keyframe_video_timestamp",
            )
        ]
        indexes = [
            models.Index(fields=["video", "is_selected"]),
            models.Index(fields=["video", "timestamp_ms"]),
            models.Index(fields=["video", "-sharpness_score"]),
        ]
