from django.conf import settings
from django.db import models


class Review(models.Model):
    class Role(models.TextChoices):
        BUYER_TO_SELLER = "buyer_to_seller"
        SELLER_TO_BUYER = "seller_to_buyer"

    order = models.ForeignKey("commerce.Order", on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_written",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_received",
    )

    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "role"], name="uniq_review_per_role_order"
            )
        ]
        indexes = [models.Index(fields=["target", "role", "created_at"])]
