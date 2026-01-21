# ai/services/analysis.py
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Optional, Union

from django.conf import settings
from django.utils import timezone


def create_analysis(
    *,
    image_asset,
    requested_by=None,
    provider: Union[str, "AIModelProvider"] = "openai",
    model_name: Optional[str] = None,
    prompt_version: str = "v1",
    status: Optional[str] = None,
    input_payload: Optional[Dict] = None,
    output_json: Optional[Dict] = None,
    error_code: str = "",
    error_message: Optional[str] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_eur: Decimal = Decimal("0.0000"),
    attempt: int = 0,
    request_id: str = "",
    completed_at=None,
) -> "AIImageAnalysis":
    from ai.models import AIImageAnalysis

    provider_value = (
        provider.value if hasattr(provider, "value") else provider
    )
    status_value = (
        status or AIImageAnalysis.Status.SUCCEEDED
    )

    return AIImageAnalysis.objects.create(
        image_asset=image_asset,
        requested_by=requested_by,
        provider=provider_value,
        model_name=model_name or settings.AI_DEFAULT_MODEL,
        prompt_version=prompt_version,
        status=status_value,
        error_code=error_code,
        error_message=error_message or "",
        input_payload=input_payload or {},
        output_json=output_json or {},
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_eur=cost_eur,
        attempt=attempt,
        request_id=request_id,
        completed_at=completed_at or timezone.now(),
    )


def create_suggestion(
    *,
    analysis: "AIImageAnalysis",
    suggested_category_slug: str = "",
    suggested_title: str = "",
    suggested_condition: str = "",
    suggested_attributes: Optional[Dict] = None,
    price_eur_min: Optional[int] = None,
    price_eur_max: Optional[int] = None,
    pricing_reason: str = "",
    quality_flags: Optional[Iterable[str]] = None,
    user_accepted: bool = False,
    accepted_at=None,
) -> "AISuggestion":
    from ai.models import AISuggestion

    return AISuggestion.objects.create(
        analysis=analysis,
        suggested_category_slug=suggested_category_slug,
        suggested_title=suggested_title,
        suggested_condition=suggested_condition,
        suggested_attributes=suggested_attributes or {},
        price_eur_min=price_eur_min,
        price_eur_max=price_eur_max,
        pricing_reason=pricing_reason,
        quality_flags=list(quality_flags or []),
        user_accepted=user_accepted,
        accepted_at=accepted_at,
    )
