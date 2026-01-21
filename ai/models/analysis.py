import uuid

from decimal import Decimal

from django.conf import settings
from django.db import models


class AIModelProvider(models.TextChoices):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    AWS = "aws"


class AIImageAnalysis(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued"
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    image_asset = models.ForeignKey(
        "ingestion.BatchMedia", on_delete=models.CASCADE, related_name="ai_analyses"
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_requests",
    )

    provider = models.CharField(
        max_length=20, choices=AIModelProvider.choices, default=AIModelProvider.OPENAI
    )
    model_name = models.CharField(
        max_length=64, default=settings.AI_DEFAULT_MODEL
    )
    prompt_version = models.CharField(max_length=24, default="v1")

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.QUEUED
    )
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(null=True, blank=True)

    input_payload = models.JSONField(default=dict, blank=True)
    output_json = models.JSONField(default=dict, blank=True)

    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_eur = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("0.0000")
    )

    attempt = models.PositiveSmallIntegerField(default=0)

    request_id = models.CharField(max_length=64, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["image_asset", "created_at"]),
            models.Index(fields=["created_at"]),
        ]
