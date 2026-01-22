import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone


class Listing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PENDING_REVIEW = "pending_review"
        PUBLISHED = "published"
        REJECTED = "rejected"
        SOLD = "sold"
        ARCHIVED = "archived"

    class Condition(models.TextChoices):
        NEW = "new"
        LIKE_NEW = "like_new"
        GOOD = "good"
        FAIR = "fair"
        FOR_PARTS = "for_parts"

    class SourceType(models.TextChoices):
        IMAGES = "images"
        VIDEO = "video"

    class PublicStatus(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        NEGOTIATING = "negotiating", "Offres en cours"
        SOLD = "sold", "Vendue"
        ARCHIVED = "archived", "Archivée"

    PUBLIC_STATUS_TONES = {
        PublicStatus.AVAILABLE: "success",
        PublicStatus.NEGOTIATING: "warning",
        PublicStatus.SOLD: "danger",
        PublicStatus.ARCHIVED: "secondary",
    }

    PUBLIC_FEED_STATUSES = {Status.PUBLISHED}

    class ChangeEvent(models.TextChoices):
        SUBMITTED = "submitted", "Annonce soumise"
        APPROVED = "approved", "Annonce validée"
        REJECTED = "rejected", "Annonce rejetée"
        STATUS_UPDATED = "status_updated", "Statut modifié"
        DETAILS_UPDATED = "details_updated", "Détails mis à jour"
        OTHER = "other", "Autre modification"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings"
    )
    category = models.ForeignKey(
        "catalog.Category",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="listings",
    )

    title = models.CharField(max_length=140, blank=True, db_index=True)
    slug = models.SlugField(max_length=160, blank=True, db_index=True)
    description = models.TextField(blank=True)
    condition = models.CharField(
        max_length=16,
        choices=Condition.choices,
        default=Condition.GOOD,
        blank=True,
        db_index=True,
    )

    price_cents = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    currency = models.CharField(max_length=3, default="EUR")

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )

    postal_code = models.CharField(max_length=20, blank=True, db_index=True)
    location_city = models.ForeignKey(
        "location.City",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listings",
    )
    country_code = models.CharField(max_length=2, default="FR")
    available_from = models.DateTimeField(null=True, blank=True, db_index=True)
    view_count = models.PositiveIntegerField(default=0, db_index=True)

    source_type = models.CharField(
        max_length=12, choices=SourceType.choices, default=SourceType.IMAGES
    )
    source_video = models.ForeignKey(
        "mediahub.VideoUpload",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listings",
    )

    shipping_enabled = models.BooleanField(default=True, db_index=True)
    in_person_enabled = models.BooleanField(default=True, db_index=True)

    # moderation
    moderation_notes = models.TextField(blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="moderated_listings",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    reports = GenericRelation(
        "reports.Report",
        content_type_field="target_content_type",
        object_id_field="target_object_id",
        related_query_name="listings",
    )
    needs_review = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["category", "status", "created_at"]),
            models.Index(fields=["postal_code", "status", "created_at"]),
            models.Index(fields=["location_city", "status", "created_at"]),
        ]

    def __str__(self):
        return self.title or f"Listing({self.id})"

    @property
    def city(self) -> str:
        return self.location_city.name if self.location_city else ""

    @property
    def change_history(self):
        return self.change_logs.order_by("-created_at")

    def get_public_status(self):
        if self.status == self.Status.PUBLISHED:
            if self.offers.active().exists():
                return self.PublicStatus.NEGOTIATING
            return self.PublicStatus.AVAILABLE
        if self.status == self.Status.SOLD:
            return self.PublicStatus.SOLD
        if self.status == self.Status.ARCHIVED:
            return self.PublicStatus.ARCHIVED
        return None

    @property
    def public_status_display(self):
        status = self.get_public_status()
        return status.label if status else ""

    @property
    def public_status_badge_tone(self):
        status = self.get_public_status()
        return self.PUBLIC_STATUS_TONES.get(status, "secondary")

    def is_listed_publicly(self):
        return self.get_public_status() in {
            self.PublicStatus.AVAILABLE,
            self.PublicStatus.NEGOTIATING,
        }

    def get_primary_image(self):
        from listings.services.images import get_primary_image

        return get_primary_image(listing=self)

    @property
    def active_reservation(self):
        from listings.queries.reservations import get_active_reservation_offer

        return get_active_reservation_offer(self)

    @property
    def reserved_for(self):
        reservation = self.active_reservation
        return getattr(reservation, "buyer", None)

    @property
    def reservation_note(self):
        reservation = self.active_reservation
        return getattr(reservation, "note", "")

    @property
    def is_reserved_state(self) -> bool:
        return bool(self.active_reservation)


class ListingView(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listing_views"
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="views"
    )
    viewed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"], name="uniq_listing_view_user_listing"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "listing"]),
            models.Index(fields=["viewed_at"]),
        ]

    def __str__(self):
        return f"{self.user} viewed {self.listing} at {self.viewed_at}"
