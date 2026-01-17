from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("mediahub", "0002_batch_metadata"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="batchupload",
            name="sale_channel",
        ),
    ]
