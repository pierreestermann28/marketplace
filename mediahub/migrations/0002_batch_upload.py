from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("mediahub", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BatchUpload",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PROCESSING", "Processing"),
                            ("DONE", "Done"),
                            ("FAILED", "Failed"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=12,
                    ),
                ),
                ("media_count", models.PositiveIntegerField(default=0)),
                (
                    "processing_started_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="batch_uploads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["owner", "status", "created_at"],
                        name="mediahub_ba_owner_status_c_2258a1_idx",
                    ),
                    models.Index(
                        fields=["status", "created_at"],
                        name="mediahub_ba_status_created__44ccef_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="MediaAsset",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "media_type",
                    models.CharField(
                        choices=[("image", "Image"), ("video", "Video")],
                        default="image",
                        max_length=12,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("upload", "Upload"),
                            ("keyframe", "Keyframe"),
                            ("other", "Other"),
                        ],
                        default="upload",
                        max_length=20,
                    ),
                ),
                ("file_hash", models.CharField(blank=True, max_length=64)),
                ("metadata_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="media_assets",
                        to="mediahub.batchupload",
                    ),
                ),
                (
                    "image_asset",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="media_asset",
                        to="mediahub.imageasset",
                    ),
                ),
            ],
        ),
    ]
