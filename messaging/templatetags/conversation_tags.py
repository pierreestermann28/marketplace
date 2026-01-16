from django import template

register = template.Library()


@register.simple_tag
def reservation_badge(listing, user):
    if not listing:
        return ""
    return listing.reservation_badge_label(user)
