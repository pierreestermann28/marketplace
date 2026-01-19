from django.conf import settings
from django.db import migrations, models

import billing.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserEntitlement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("is_premium", models.BooleanField(db_index=True, default=False)),
                ("premium_until", models.DateTimeField(blank=True, null=True)),
                ("free_listing_quota", models.PositiveIntegerField(default=3)),
                ("free_detected_item_quota", models.PositiveIntegerField(default=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        related_name="entitlement",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User entitlement",
                "verbose_name_plural": "User entitlements",
            },
        ),
        migrations.CreateModel(
            name="UsageCounter",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("scope", models.CharField(db_index=True, max_length=64)),
                (
                    "period",
                    models.DateField(
                        db_index=True,
                        default=billing.models.current_month_period,
                    ),
                ),
                ("count", models.PositiveIntegerField(default=0)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="usage_counters",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"unique_together": {("user", "scope", "period")}},
        ),
    ]
