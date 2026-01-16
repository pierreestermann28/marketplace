from django.conf import settings
from django.core.mail import mail_admins
from django.urls import reverse


def notify_batch_failure(batch):
    if not settings.ADMINS:
        return
    subject = f"[StillUseful] Batch {batch.id} failed"
    base_url = getattr(settings, "SITE_URL", "").rstrip("/")
    batch_url = f"{base_url}{reverse('ingestion:batch_processing', kwargs={'batch_id': batch.id})}"
    message = "\n".join(
        [
            f"Batch #{batch.id} a échoué.",
            f"Propriétaire : {batch.owner.get_full_name() or batch.owner.email}",
            f"Statut : {batch.get_status_display()}",
            f"Nombre de médias : {batch.media_count}",
            f"Erreur : {batch.error_message or 'Non renseignée'}",
            f"Page : {batch_url}",
        ]
    )
    mail_admins(subject, message)
