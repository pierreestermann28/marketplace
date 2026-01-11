import random
from decimal import Decimal

from celery import shared_task
from django.db import transaction

from mediahub.models import BatchUpload
from .models import DetectedItem


@shared_task(bind=True, name="ingestion.analyze_batch", max_retries=1)
def analyze_batch(self, batch_id):
    try:
        batch = (
            BatchUpload.objects.select_related("owner")
            .prefetch_related("media_assets__image_asset")
            .get(id=batch_id)
        )
    except BatchUpload.DoesNotExist:
        return

    if batch.status == BatchUpload.Status.DONE:
        return

    batch.mark_processing()
    assets = list(batch.media_assets.all())
    if not assets:
        batch.mark_failed("No assets found for batch")
        return

    suggestions = []
    try:
        for asset in assets:
            for index in range(random.randint(1, 3)):
                price = Decimal("25.00") + Decimal(index * 10)
                low = price
                high = price + Decimal("15.00")
                title = asset.image_asset.image.name.split("/")[-1]
                description = (
                    f"Objet détecté {index + 1} issu de {asset.batch.owner.get_full_name() or asset.batch.owner.email}"
                )
                confidence = random.uniform(0.5, 0.98)
                suggestions.append(
                    DetectedItem(
                        owner=batch.owner,
                        batch=batch,
                        hero_asset=asset,
                        title_suggested=title or "Objet détecté",
                        description_suggested=description,
                        category_suggested="Misc",
                        price_low=low,
                        price_high=high,
                        confidence=confidence,
                        metadata_json={
                            "asset_id": str(asset.id),
                            "media_type": asset.media_type,
                            "confidence": confidence,
                        },
                    )
                )
    except Exception as exc:  # pragma: no cover
        batch.mark_failed(str(exc))
        raise

    with transaction.atomic():
        DetectedItem.objects.bulk_create(suggestions)
        batch.mark_done()
