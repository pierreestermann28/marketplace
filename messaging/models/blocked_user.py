from django.conf import settings
from django.db import models


class BlockedUser(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks",
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocked_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="uniq_blocked_user_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["blocker", "created_at"]),
            models.Index(fields=["blocked", "created_at"]),
        ]
