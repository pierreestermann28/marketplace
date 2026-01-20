# messaging/services/messages.py
from django.db import transaction

from messaging.models import Message, Conversation


@transaction.atomic
def send_message(
    *,
    conversation: Conversation,
    sender,
    text: str = "",
    attachment=None,
) -> Message:
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        text=text,
        attachment=attachment,
    )

    Conversation.objects.filter(pk=conversation.pk).update(
        last_message_at=message.created_at
    )

    return message
