from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from billing.models import UserEntitlement


@receiver(post_save, sender=get_user_model())
def ensure_entitlement(sender, instance, created, **kwargs):
    if created:
        UserEntitlement.objects.get_or_create(user=instance)
