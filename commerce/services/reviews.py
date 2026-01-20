# commerce/services/reviews.py
from django.db import IntegrityError, transaction

from commerce.models import Order, Review


class ReviewNotAllowed(Exception):
    pass


@transaction.atomic
def create_review(
    *, order: Order, author, rating: int, comment: str = "", tags=None
) -> Review:
    if order.status != Order.Status.COMPLETED:
        raise ReviewNotAllowed("Order not completed")

    if author.id == order.buyer_id:
        role = Review.Role.BUYER_TO_SELLER
        target = order.seller
    elif author.id == order.seller_id:
        role = Review.Role.SELLER_TO_BUYER
        target = order.buyer
    else:
        raise ReviewNotAllowed("Not a participant")

    rating = int(rating)
    if rating < 1 or rating > 5:
        raise ValueError("rating must be 1..5")

    try:
        return Review.objects.create(
            order=order,
            author=author,
            target=target,
            role=role,
            rating=rating,
            comment=comment or "",
            tags=tags or [],
        )
    except IntegrityError:
        raise ReviewNotAllowed("Review already exists for this role")
