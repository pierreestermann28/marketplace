from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserEntitlement",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("is_premium", models.BooleanField(default=False, db_index=True)),
                ("premium_until", models.DateTimeField(blank=True, null=True)),
                ("free_listing_quota", models.PositiveIntegerField(default=3)),
                ("free_detected_item_quota", models.PositiveIntegerField(default=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
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
    ]
