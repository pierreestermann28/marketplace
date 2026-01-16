from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from listings.models import Listing


class Conversation(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="conversations"
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="buyer_conversations",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seller_conversations",
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reports = GenericRelation(
        "reports.Report",
        content_type_field="target_content_type",
        object_id_field="target_object_id",
        related_query_name="conversation_reports",
    )

    class Meta:
        unique_together = [("listing", "buyer")]

    def other_user(self, user):
        return self.seller if self.buyer == user else self.buyer

    def mark_messages_read_for(self, user):
        if not user:
            return
        self.messages.exclude(sender=user).filter(is_read=False).update(is_read=True)

    def unread_messages_count_for(self, user):
        if not user:
            return 0
        return self.messages.exclude(sender=user).filter(is_read=False).count()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_sent"
    )
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to="chat_attachments/%Y/%m/%d/", blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


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
        unique_together = [("blocker", "blocked")]
