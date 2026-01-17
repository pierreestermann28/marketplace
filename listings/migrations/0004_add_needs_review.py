from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0003_listing_changelog"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="needs_review",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
