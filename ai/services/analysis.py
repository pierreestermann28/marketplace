# ai/services/analysis.py
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List, Optional

from django.conf import settings
from django.utils import timezone

from ai.models import AIImageAnalysis, AISuggestion, AIModelProvider


def create_analysis(
    *,
    image_asset,
    requested_by=None,
    provider: AIModelProvider | str = AIModelProvider.OPENAI,
    model_name: str | None = None,
    prompt_version: str = "v1",
    status: AIImageAnalysis.Status = AIImageAnalysis.Status.SUCCEEDED,
    input_payload: Optional[Dict] = None,
    output_json: Optional[Dict] = None,
    error_code: str = "",
    error_message: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_eur: Decimal = Decimal("0.0000"),
    attempt: int = 0,
    request_id: str = "",
    completed_at=None,
) -> AIImageAnalysis:
    return AIImageAnalysis.objects.create(
        image_asset=image_asset,
        requested_by=requested_by,
        provider=provider,
        model_name=model_name or settings.AI_DEFAULT_MODEL,
        prompt_version=prompt_version,
        status=status,
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
    analysis: AIImageAnalysis,
    suggested_category_slug: str = "",
    suggested_title: str = "",
    suggested_condition: str = "",
    suggested_attributes: Optional[Dict] = None,
    price_eur_min: Optional[int] = None,
    price_eur_max: Optional[int] = None,
    pricing_reason: str = "",
    quality_flags: Iterable[str] | None = None,
    user_accepted: bool = False,
    accepted_at=None,
) -> AISuggestion:
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
