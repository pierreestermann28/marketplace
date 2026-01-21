from django.utils import timezone


def current_month_period():
    today = timezone.localdate()
    return today.replace(day=1)
