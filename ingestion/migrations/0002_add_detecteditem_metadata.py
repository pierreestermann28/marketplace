from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="detecteditem",
            name="metadata_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
