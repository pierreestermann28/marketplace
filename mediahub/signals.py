from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .alerts import notify_batch_failure
from ingestion.models import BatchUpload


@receiver(pre_save, sender=BatchUpload)
def cache_previous_batch_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
    else:
        instance._previous_status = (
            sender.objects.filter(pk=instance.pk)
            .values_list("status", flat=True)
            .first()
        )


@receiver(post_save, sender=BatchUpload)
def send_failure_alert(sender, instance, **kwargs):
    previous_status = getattr(instance, "_previous_status", None)
    if (
        instance.status == BatchUpload.Status.FAILED
        and previous_status != BatchUpload.Status.FAILED
    ):
        notify_batch_failure(instance)
