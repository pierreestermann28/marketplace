from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0002_alter_searchalert_unique_together_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ListingChangeLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("actor_role", models.CharField(choices=[("seller", "Vendeur"), ("admin", "Admin"), ("system", "Système")], default="seller", max_length=16)),
                ("event", models.CharField(choices=[("submitted", "Annonce soumise"), ("approved", "Annonce validée"), ("rejected", "Annonce rejetée"), ("status_updated", "Statut modifié"), ("details_updated", "Détails mis à jour"), ("other", "Autre modification")], max_length=24)),
                ("details", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "listing",
                    models.ForeignKey(on_delete=models.CASCADE, related_name="change_logs", to="listings.listing"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
