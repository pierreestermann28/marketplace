from django import template

register = template.Library()


@register.filter
def human_role(value):
    if not value:
        return ""

    labels = {
        "buyer_to_seller": "Acheteur vers vendeur",
        "seller_to_buyer": "Vendeur vers acheteur",
    }

    return labels.get(value, value.replace("_", " ").title())


@register.filter
def initials(user):
    if not user:
        return ""
    names = []
    if getattr(user, "first_name", None):
        names.append(user.first_name.strip())
    if getattr(user, "last_name", None):
        names.append(user.last_name.strip())
    if names:
        initials = "".join(name[0].upper() for name in (names[0], names[-1]) if name)
        return initials[:2]
    if getattr(user, "email", None):
        return user.email[:2].upper()
    return ""


@register.filter
def rating_stars(value):
    try:
        avg = float(value or 0)
    except (TypeError, ValueError):
        avg = 0

    stars = []
    for idx in range(1, 6):
        if avg >= idx:
            stars.append("full")
        elif avg >= idx - 0.5:
            stars.append("half")
        else:
            stars.append("empty")
    return stars
