from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
        ("listings", "0004_add_needs_review"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OnboardingProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("buy", "Acheter"),
                            ("sell", "Vendre"),
                            ("both", "Acheter & Vendre"),
                        ],
                        default="buy",
                        max_length=10,
                    ),
                ),
                ("city", models.CharField(blank=True, max_length=80)),
                ("radius_km", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        related_name="onboarding_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="onboardingprofile",
            name="categories",
            field=models.ManyToManyField(
                blank=True,
                related_name="onboarding_profiles",
                to="catalog.Category",
            ),
        ),
    ]
