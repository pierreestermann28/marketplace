from django.db.models import QuerySet


def get_recent_reviews_for_user(user, limit: int = 5) -> QuerySet:
    return (
        user.reviews_received.select_related("order__listing")
        .order_by("-created_at")[:limit]
    )
