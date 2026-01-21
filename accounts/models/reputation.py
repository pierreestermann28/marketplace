from decimal import Decimal

from django.conf import settings
from django.db import models


class ReputationStats(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reputation"
    )

    seller_rating_avg = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal("0.00")
    )
    seller_rating_count = models.PositiveIntegerField(default=0)

    buyer_rating_avg = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal("0.00")
    )
    buyer_rating_count = models.PositiveIntegerField(default=0)

    items_sold_count = models.PositiveIntegerField(default=0)
    items_bought_count = models.PositiveIntegerField(default=0)

    cancellations_count = models.PositiveIntegerField(default=0)
    no_show_count = models.PositiveIntegerField(default=0)
    disputes_count = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)
