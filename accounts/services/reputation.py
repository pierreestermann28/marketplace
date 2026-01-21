# accounts/services/reputation.py
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from accounts.models import ReputationStats, User


class ReputationError(Exception):
    pass


@transaction.atomic
def rebuild_reputation_for_user(*, user: User) -> ReputationStats:
    """
    Rebuilds ReputationStats from source-of-truth tables:
    - commerce.Review for ratings (seller + buyer)
    - commerce.Order for sold/bought counts (COMPLETED)
    Also updates User.trust_score = weighted avg of both sides.
    """
    from commerce.models import Review, Order  # local import to avoid circular deps

    stats = ReputationStats.objects.select_for_update().get_or_create(user=user)[0]

    seller_reviews = Review.objects.filter(
        target=user, role=Review.Role.BUYER_TO_SELLER
    )
    buyer_reviews = Review.objects.filter(target=user, role=Review.Role.SELLER_TO_BUYER)

    def avg_from_queryset(qs) -> Decimal:
        data = qs.aggregate(avg=Avg("rating"))
        return Decimal(str(data["avg"] or 0)).quantize(Decimal("0.01"))

    # Reviews
    stats.seller_rating_count = seller_reviews.count()
    stats.seller_rating_avg = avg_from_queryset(seller_reviews)

    stats.buyer_rating_count = buyer_reviews.count()
    stats.buyer_rating_avg = avg_from_queryset(buyer_reviews)

    # Transactions
    stats.items_sold_count = Order.objects.filter(
        seller=user, status=Order.Status.COMPLETED
    ).count()
    stats.items_bought_count = Order.objects.filter(
        buyer=user, status=Order.Status.COMPLETED
    ).count()

    stats.save(
        update_fields=[
            "seller_rating_avg",
            "seller_rating_count",
            "buyer_rating_avg",
            "buyer_rating_count",
            "items_sold_count",
            "items_bought_count",
            "updated_at",
        ]
    )

    # Trust score = weighted avg of both sides
    total = stats.seller_rating_count + stats.buyer_rating_count
    if total > 0:
        trust = (
            (stats.seller_rating_avg * stats.seller_rating_count)
            + (stats.buyer_rating_avg * stats.buyer_rating_count)
        ) / Decimal(total)
    else:
        trust = Decimal("0.00")

    trust = trust.quantize(Decimal("0.01"))

    User.objects.filter(pk=user.pk).update(trust_score=trust)
    return stats


def ensure_reputation_stats(*, user: User) -> ReputationStats:
    stats, _ = ReputationStats.objects.get_or_create(user=user)
    return stats
