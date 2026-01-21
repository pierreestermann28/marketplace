from __future__ import annotations


def ban_user(user) -> None:
    user.is_active = False
    user.save(update_fields=["is_active"])
