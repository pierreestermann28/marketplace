from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mediahub", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="batchupload",
            name="sale_location",
            field=models.CharField(blank=True, db_index=True, max_length=140),
        ),
        migrations.AddField(
            model_name="batchupload",
            name="sale_channel",
            field=models.CharField(
                blank=True,
                choices=[
                    ("MARKETPLACE", "Marketplace StillUseful"),
                    ("BOUTIQUE", "Boutique / dépôt local"),
                    ("SOCIAL", "Réseaux sociaux"),
                    ("OTHER", "Autres canaux"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="batchupload",
            name="seller_notes",
            field=models.TextField(blank=True),
        ),
    ]
