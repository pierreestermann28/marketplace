from django.conf import settings
from django.db import models

from messaging.models.conversation import Conversation


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages_sent",
    )

    text = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="chat_attachments/%Y/%m/%d/",
        null=True,
        blank=True,
    )

    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["conversation", "is_read"]),
        ]
