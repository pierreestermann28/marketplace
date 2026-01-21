from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Report(models.Model):
    class Reason(models.TextChoices):
        SCAM = "scam", "Arnaque"
        ILLEGAL = "illegal", "Contenu illégal"
        INAPPROPRIATE = "inappropriate", "Inapproprié"
        SPAM = "spam", "Spam"
        OTHER = "other", "Autre"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_created",
    )
    reason = models.CharField(max_length=32, choices=Reason.choices)
    details = models.TextField(blank=True)

    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="reported_objects",
    )
    target_object_id = models.CharField(max_length=64, db_index=True)
    target = GenericForeignKey("target_content_type", "target_object_id")

    is_resolved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports_resolved",
    )

    target_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_resolved", "created_at"]),
            models.Index(fields=["reason", "is_resolved", "created_at"]),
            models.Index(fields=["target_content_type", "target_object_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "target_content_type", "target_object_id"],
                name="unique_report_per_user_target",
            )
        ]

    def __str__(self):
        return f"{self.get_reason_display()} report by user#{self.reporter_id}"

    @property
    def target_label(self):
        target = self.target
        if not target:
            return str(self.target_object_id)
        if hasattr(target, "title") and getattr(target, "title"):
            return target.title
        associated = getattr(target, "listing", None)
        if associated and hasattr(associated, "title"):
            return associated.title
        return str(target)

    @property
    def target_type(self):
        return self.target_content_type.model if self.target_content_type else "target"
