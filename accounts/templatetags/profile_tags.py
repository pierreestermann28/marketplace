from django import template

register = template.Library()


@register.filter
def human_role(value):
    if not value:
        return ""
    return value.replace("_", " ").title()
