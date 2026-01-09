from decimal import Decimal

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver


class EmailUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        return super()._create_user(email=email, password=password, **extra_fields)

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)
    display_name = models.CharField(max_length=80, blank=True)
    phone_e164 = models.CharField(max_length=32, blank=True, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    trust_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = EmailUserManager()


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    label = models.CharField(max_length=60, default="Home")
    full_name = models.CharField(max_length=120)
    line1 = models.CharField(max_length=120)
    line2 = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=20, db_index=True)
    city = models.CharField(max_length=80, db_index=True)
    country_code = models.CharField(max_length=2, default="FR")
    phone_e164 = models.CharField(max_length=32, blank=True)

    is_default = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ReputationStats(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reputation",
    )

    seller_rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    seller_rating_count = models.PositiveIntegerField(default=0)
    items_sold_count = models.PositiveIntegerField(default=0)

    buyer_rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    buyer_rating_count = models.PositiveIntegerField(default=0)
    items_bought_count = models.PositiveIntegerField(default=0)

    cancellations_count = models.PositiveIntegerField(default=0)
    no_show_count = models.PositiveIntegerField(default=0)
    disputes_count = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def for_user(cls, user):
        stats, _ = cls.objects.get_or_create(user=user)
        return stats

    def rebuild_from_reviews(self):
        from commerce.models import Review

        seller_reviews = Review.objects.filter(
            target=self.user, role=Review.Role.BUYER_TO_SELLER
        )
        buyer_reviews = Review.objects.filter(
            target=self.user, role=Review.Role.SELLER_TO_BUYER
        )

        def avg_from_queryset(qs):
            data = qs.aggregate(avg=Avg("rating"))
            return Decimal(data["avg"] or 0)

        self.seller_rating_count = seller_reviews.count()
        self.seller_rating_avg = avg_from_queryset(seller_reviews)
        self.items_sold_count = seller_reviews.count()
        self.buyer_rating_count = buyer_reviews.count()
        self.buyer_rating_avg = avg_from_queryset(buyer_reviews)
        self.items_bought_count = buyer_reviews.count()
        self.save(
            update_fields=[
                "seller_rating_avg",
                "seller_rating_count",
                "items_sold_count",
                "buyer_rating_avg",
                "buyer_rating_count",
                "items_bought_count",
                "updated_at",
            ]
        )
        preferred_score = self.seller_rating_avg or self.buyer_rating_avg
        self.user.trust_score = preferred_score
        self.user.save(update_fields=["trust_score"])


@receiver(post_save, sender=User)
def ensure_reputation_stats(sender, instance, created, **kwargs):
    if created:
        ReputationStats.objects.get_or_create(user=instance)
