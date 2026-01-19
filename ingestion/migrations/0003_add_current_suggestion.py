from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0001_initial"),
        ("ingestion", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="detecteditem",
            name="current_suggestion",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="+",
                to="ai.aisuggestion",
            ),
        ),
    ]
