from django.db import models
from django.db.models.functions import Lower


class City(models.Model):
    """Administrative city information for fast lookup and autocomplete."""

    name = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=10)
    slug = models.SlugField(max_length=140, unique=True)
    department_code = models.CharField(max_length=3, blank=True)
    department_name = models.CharField(max_length=120, blank=True)
    region_code = models.CharField(max_length=3, blank=True)
    region_name = models.CharField(max_length=120, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    class Meta:
        ordering = ["name", "postal_code"]
        indexes = [
            models.Index(fields=["postal_code"], name="location_city_postal_idx"),
            models.Index(fields=["name"], name="location_city_name_idx"),
            models.Index(
                fields=["name", "postal_code"], name="location_city_name_postal_idx"
            ),
            models.Index(Lower("name"), name="location_city_name_lower_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "postal_code"], name="location_city_name_postal_uniq"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.postal_code})"
