from __future__ import annotations


def set_premium_status(entitlement, enable: bool) -> str:
    entitlement.is_premium = enable
    entitlement.premium_until = None
    entitlement.save(update_fields=["is_premium", "premium_until", "updated_at"])
    if enable:
        return f"Premium activé pour {entitlement.user.get_full_name() or entitlement.user.email}."
    return f"Premium suspendu pour {entitlement.user.get_full_name() or entitlement.user.email}."
