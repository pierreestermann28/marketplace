from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    ai_hints = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["parent", "name"])]

    def __str__(self):
        return self.name
