from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="detecteditem",
            name="is_cached_result",
            field=models.BooleanField(
                default=False,
                db_index=True,
            ),
        ),
    ]
