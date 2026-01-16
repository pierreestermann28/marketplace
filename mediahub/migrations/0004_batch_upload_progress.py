from django.db import migrations, models


def forward_update_status(apps, schema_editor):
    BatchUpload = apps.get_model("mediahub", "BatchUpload")
    BatchUpload.objects.filter(status="PROCESSING").update(status="RUNNING")


def backward_update_status(apps, schema_editor):
    BatchUpload = apps.get_model("mediahub", "BatchUpload")
    BatchUpload.objects.filter(status="RUNNING").update(status="PROCESSING")


class Migration(migrations.Migration):

    dependencies = [
        ("mediahub", "0003_rename_mediahub_ba_owner_status_c_2258a1_idx_mediahub_ba_owner_i_cf00dd_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="batchupload",
            name="processed_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(forward_update_status, backward_update_status),
    ]
