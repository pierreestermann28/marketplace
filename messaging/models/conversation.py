from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models


class Conversation(models.Model):
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="conversations",
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
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "buyer"],
                name="uniq_conversation_listing_buyer",
            ),
        ]
        indexes = [
            models.Index(fields=["buyer", "-last_message_at"]),
            models.Index(fields=["seller", "-last_message_at"]),
            models.Index(fields=["listing", "-last_message_at"]),
        ]
