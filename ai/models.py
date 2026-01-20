import uuid
from django.conf import settings
from django.db import models
from decimal import Decimal


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
        "mediahub.BatchMedia", on_delete=models.CASCADE, related_name="ai_analyses"
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
    )  # example
    prompt_version = models.CharField(max_length=24, default="v1")

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.QUEUED
    )
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(null=True, blank=True)

    # Store what you sent + what you got back (debuggable + replayable)
    input_payload = models.JSONField(default=dict, blank=True)
    output_json = models.JSONField(default=dict, blank=True)

    # Cost tracking (optional but very useful)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_eur = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("0.0000")
    )

    # Retry
    attempt = models.PositiveSmallIntegerField(default=0)

    # Already done
    request_id = models.CharField(max_length=64, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["image_asset", "created_at"]),
            models.Index(fields=["created_at"]),
        ]


class AISuggestion(models.Model):
    """
    A normalized suggestion extracted from AIImageAnalysis.output_json
    to prefill the listing form and track acceptance.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    analysis = models.OneToOneField(
        AIImageAnalysis, on_delete=models.CASCADE, related_name="suggestion"
    )
    listing = models.ForeignKey(
        "listings.Listing",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_suggestions",
    )

    # Suggested fields (keep it close to your Listing fields)
    suggested_category_slug = models.CharField(max_length=64, blank=True)
    suggested_title = models.CharField(max_length=120, blank=True)
    suggested_condition = models.CharField(
        max_length=20, blank=True
    )  # new/like_new/good/used/poor
    suggested_attributes = models.JSONField(default=dict)
    price_eur_min = models.PositiveIntegerField(null=True, blank=True)
    price_eur_max = models.PositiveIntegerField(null=True, blank=True)

    pricing_reason = models.CharField(max_length=280, blank=True)
    quality_flags = models.JSONField(default=list, blank=True)  # ["blur", "dark", ...]

    # Did the user accept it?
    user_accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
