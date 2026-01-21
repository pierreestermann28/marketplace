# messaging/services/conversations.py
from datetime import datetime
from typing import Optional, Tuple

from django.db import transaction

from messaging.models import Conversation, Message


def get_other_user(conversation: Conversation, user):
    if not user:
        return None
    if conversation.buyer_id == user.id:
        return conversation.seller
    if conversation.seller_id == user.id:
        return conversation.buyer
    return None


def mark_messages_read(conversation: Conversation, user) -> int:
    if not user:
        return 0

    return (
        conversation.messages.exclude(sender=user)
        .filter(is_read=False)
        .update(is_read=True)
    )


def unread_messages_count(conversation: Conversation, user) -> int:
    if not user:
        return 0

    return conversation.messages.exclude(sender=user).filter(is_read=False).count()


@transaction.atomic
def get_or_create_conversation(
    *, listing, buyer, seller, initial_last_message_at: Optional[datetime] = None
) -> Tuple[Conversation, bool]:
    conversation, created = Conversation.objects.get_or_create(
        listing=listing,
        buyer=buyer,
        defaults={"seller": seller},
    )
    if created and initial_last_message_at is not None:
        conversation.last_message_at = initial_last_message_at
        conversation.save(update_fields=["last_message_at"])
    return conversation, created
