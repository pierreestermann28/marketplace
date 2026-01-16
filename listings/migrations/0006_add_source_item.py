from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0005_searchalert_searchalertnotification"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="source_item",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="published_listing",
                to="ingestion.detecteditem",
            ),
        ),
    ]
