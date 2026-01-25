import hashlib
import logging
import random
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ingestion.services import mark_processing, mark_failed, mark_done

try:
    from celery import shared_task
except ImportError:  # pragma: no cover

    def shared_task(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


logger = logging.getLogger("ingestion.tasks")

from ai.models import AIImageAnalysis, AIModelProvider
from ai.services import create_analysis, create_suggestion
from billing.entitlements import (
    detected_item_usage_window,
    get_free_detected_item_quota,
    is_premium,
)
from ingestion.models import BatchUpload
from ingestion.services.batches import mark_processing, mark_done, mark_failed
from .models import DetectedItem


def _compute_file_hash(asset):
    path = asset.image_asset.image.path
    hasher = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _ensure_asset_hash(asset):
    if asset.file_hash:
        return asset.file_hash
    file_hash = _compute_file_hash(asset)
    if file_hash:
        asset.file_hash = file_hash
        asset.save(update_fields=["file_hash"])
    return file_hash


def _find_cached_detected_item(owner, file_hash):
    if not file_hash:
        return None
    return (
        DetectedItem.objects.filter(
            owner=owner,
            hero_asset__file_hash=file_hash,
        )
        .order_by("-updated_at")
        .first()
    )


def _create_detected_from_cache(batch, asset, cached):
    DetectedItem.objects.create(
        owner=batch.owner,
        batch=batch,
        hero_asset=asset,
        status=cached.status,
        current_suggestion=cached.current_suggestion,
    )
    batch.mark_asset_processed()


def _create_detected_from_analysis(batch, asset, *, stub=False):
    price = Decimal("25.00")
    low = price
    high = price + Decimal("15.00")
    owner_label = asset.batch.owner.get_full_name() or asset.batch.owner.email
    title = (
        f"Titre généré par l’IA – {asset.image_asset.image.name.split('/')[-1]}"
        if stub
        else asset.image_asset.image.name.split("/")[-1]
    )
    description = (
        "Description générée par l’IA pour alimenter la preview."
        if stub
        else f"Objet détecté issu de {owner_label}"
    )
    confidence = random.uniform(0.6, 0.9) if stub else random.uniform(0.5, 0.98)
    analysis = create_analysis(
        image_asset=asset,
        requested_by=batch.owner,
        provider=AIModelProvider.OPENAI,
        status=AIImageAnalysis.Status.SUCCEEDED,
        input_payload={"asset_id": str(asset.id)},
        output_json={
            "description": description,
            "confidence": confidence,
            "price_low": float((low.quantize(ROUND_HALF_UP)) if low is not None else 0),
            "price_high": float(
                (high.quantize(ROUND_HALF_UP)) if high is not None else 0
            ),
        },
        completed_at=timezone.now(),
    )
    suggestion = create_suggestion(
        analysis=analysis,
        suggested_title=title or "Objet détecté",
        suggested_category_slug="Décoration" if stub else "Misc",
        price_eur_min=int(low.quantize(ROUND_HALF_UP)),
        price_eur_max=int(high.quantize(ROUND_HALF_UP)),
        pricing_reason="IA heuristics – batch upload",
        quality_flags=[asset.media_type] if asset.media_type else [],
    )
    DetectedItem.objects.create(
        owner=batch.owner,
        batch=batch,
        hero_asset=asset,
        title_suggested=title or "Objet détecté",
        description_suggested=description,
        category_suggested="Misc",
        price_low=low,
        price_high=high,
        confidence=confidence,
        metadata_json=metadata,
        current_suggestion=suggestion,
    )
    batch.mark_asset_processed()


@shared_task(bind=True, name="ingestion.analyze_batch", max_retries=1)
def analyze_batch(self, batch_id):
    logger.info("Celery analyze_batch start", extra={"batch_id": str(batch_id)})
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

    mark_processing(batch=batch)
    assets = list(batch.media_assets.all())
    if not assets:
        mark_failed(batch=batch, message="No assets found for batch")
        return

    owner_premium = is_premium(batch.owner)
    usage = detected_item_usage_window(batch.owner)
    quota_limit = None if owner_premium else get_free_detected_item_quota(batch.owner)

    try:
        with transaction.atomic():
            for asset in assets:
                file_hash = _ensure_asset_hash(asset)
                cached = _find_cached_detected_item(batch.owner, file_hash)
                if cached:
                    _create_detected_from_cache(batch, asset, cached)
                    continue

                if quota_limit is not None and usage >= quota_limit:
                    mark_failed(
                        batch=batch,
                        message="Quota mensuel d’IA atteint. Passez à l’abonnement pour continuer.",
                    )
                    logger.warning(
                        "Detected item quota exceeded",
                        extra={
                            "batch_id": str(batch.id),
                            "owner_id": batch.owner_id,
                            "quota_limit": quota_limit,
                        },
                    )
                    return

                if not settings.AI_ENABLE_DETECTION:
                    _create_detected_from_analysis(batch, asset, stub=True)
                else:
                    _create_detected_from_analysis(batch, asset)
                    usage += 1

        mark_done(batch=batch)
        logger.info(
            "Celery analyze_batch completed",
            extra={"batch_id": str(batch.id), "processed_count": len(assets)},
        )
    except Exception as exc:  # pragma: no cover
        mark_failed(batch=batch, message=str(exc))
        raise
