from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0006_add_source_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="reserved_for",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="reserved_listings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="reserved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="reservation_note",
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name="ReservationLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("action", models.CharField(choices=[("reserved", "Réservé"), ("cancelled", "Annulé"), ("accepted", "Accepté")], db_index=True, max_length=16)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "listing",
                    models.ForeignKey(on_delete=models.CASCADE, related_name="reservation_logs", to="listings.listing"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.CASCADE, related_name="reservation_logs", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
