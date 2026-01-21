from django.conf import settings
from django.core.cache import cache

from messaging.services import is_blocked

CONVERSATION_RATE_LIMIT = 5
CONVERSATION_RATE_WINDOW = 3600
MESSAGE_RATE_LIMIT = 20
MESSAGE_RATE_WINDOW = 60


def increment_rate(key, window):
    count = cache.get(key)
    if count is None:
        cache.set(key, 1, window)
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        return 1


def is_blocked_pair(sender, receiver):
    if not sender or not receiver:
        return False
    return is_blocked(sender=sender, receiver=receiver) or is_blocked(
        sender=receiver, receiver=sender
    )
