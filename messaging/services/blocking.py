# messaging/services/blocking.py
from messaging.models import BlockedUser


def block_user(*, blocker, blocked) -> BlockedUser:
    block, _ = BlockedUser.objects.get_or_create(
        blocker=blocker,
        blocked=blocked,
    )
    return block


def unblock_user(*, blocker, blocked) -> None:
    BlockedUser.objects.filter(
        blocker=blocker,
        blocked=blocked,
    ).delete()


def is_blocked(*, sender, receiver) -> bool:
    return BlockedUser.objects.filter(
        blocker=receiver,
        blocked=sender,
    ).exists()
