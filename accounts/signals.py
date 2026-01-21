# commerce/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from commerce.models import Review, Order
from accounts.models import User
from accounts.services.reputation import (
    ensure_reputation_stats,
    rebuild_reputation_for_user,
)


@receiver(post_save, sender=Review)
def on_review_created(sender, instance: Review, created, **kwargs):
    if created:
        rebuild_reputation_for_user(user=instance.target)


@receiver(post_save, sender=Order)
def on_order_updated(sender, instance: Order, created, **kwargs):
    if instance.status == Order.Status.COMPLETED:
        rebuild_reputation_for_user(user=instance.seller)
        rebuild_reputation_for_user(user=instance.buyer)


@receiver(post_save, sender=User)
def ensure_reputation_on_create(sender, instance: User, created, **kwargs):
    if created:
        ensure_reputation_stats(user=instance)
