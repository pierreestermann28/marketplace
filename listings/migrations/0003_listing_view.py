from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0002_auto_add_listing_fields_and_reminders"),
    ]

    operations = [
        migrations.CreateModel(
            name="ListingView",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("viewed_at", models.DateTimeField(db_index=True, default=timezone.now)),
                (
                    "listing",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="views",
                        to="listings.listing",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="listing_views",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("user", "listing")},
            },
        ),
        migrations.AddIndex(
            model_name="listingview",
            index=models.Index(fields=["viewed_at"], name="listingview_viewed_idx"),
        ),
    ]
