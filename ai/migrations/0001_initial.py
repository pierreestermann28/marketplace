import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("listings", "0001_initial"),
        ("mediahub", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIImageAnalysis",
            fields=[
                (
                    "id",
                    models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False),
                ),
                (
                    "listing",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="ai_analyses",
                        to="listings.listing",
                    ),
                ),
                (
                    "image_asset",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="ai_analyses",
                        to="mediahub.mediaasset",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="ai_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        choices=[
                            ("openai", "OPENAI"),
                            ("azure_openai", "AZURE_OPENAI"),
                            ("aws", "AWS"),
                        ],
                        default="openai",
                        max_length=20,
                    ),
                ),
                ("model_name", models.CharField(default="gpt-4o-mini", max_length=64)),
                ("prompt_version", models.CharField(default="v1", max_length=24)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "queued"),
                            ("running", "running"),
                            ("succeeded", "succeeded"),
                            ("failed", "failed"),
                        ],
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("error_code", models.CharField(blank=True, max_length=64)),
                ("error_message", models.TextField(blank=True)),
                ("input_payload", models.JSONField(blank=True, default=dict)),
                ("output_json", models.JSONField(blank=True, default=dict)),
                ("input_tokens", models.PositiveIntegerField(default=0)),
                ("output_tokens", models.PositiveIntegerField(default=0)),
                ("cost_usd", models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["status", "created_at"], name="ai_imageanalysis_status_created_at_idx"),
                    models.Index(fields=["image_asset", "created_at"], name="ai_imageanalysis_image_asset_created_at_idx"),
                    models.Index(fields=["listing", "created_at"], name="ai_imageanalysis_listing_created_at_idx"),
                ]
            },
        ),
        migrations.CreateModel(
            name="AISuggestion",
            fields=[
                (
                    "id",
                    models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False),
                ),
                (
                    "analysis",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        related_name="suggestion",
                        to="ai.aiimageanalysis",
                    ),
                ),
                (
                    "listing",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="ai_suggestions",
                        to="listings.listing",
                    ),
                ),
                ("suggested_category_slug", models.CharField(blank=True, max_length=64)),
                ("suggested_title", models.CharField(blank=True, max_length=120)),
                ("suggested_condition", models.CharField(blank=True, max_length=20)),
                ("price_eur_min", models.PositiveIntegerField(default=0)),
                ("price_eur_max", models.PositiveIntegerField(default=0)),
                ("pricing_reason", models.CharField(blank=True, max_length=280)),
                ("quality_flags", models.JSONField(blank=True, default=list)),
                ("user_accepted", models.BooleanField(default=False)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
