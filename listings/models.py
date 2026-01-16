import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import F, Prefetch
from django.utils import timezone
from django.utils.text import slugify

from catalog.models import Category
from mediahub.models import ImageAsset, Keyframe, VideoUpload


class Listing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PENDING_REVIEW = "pending_review"
        PUBLISHED = "published"
        REJECTED = "rejected"
        RESERVED = "reserved"
        RESERVATION_ACCEPTED = "reservation_accepted"
        SOLD = "sold"
        ARCHIVED = "archived"

    class Condition(models.TextChoices):
        NEW = "new"
        LIKE_NEW = "like_new"
        GOOD = "good"
        FAIR = "fair"
        FOR_PARTS = "for_parts"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings"
    )
    category = models.ForeignKey(
        Category,
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
    city = models.CharField(max_length=80, blank=True, db_index=True)
    country_code = models.CharField(max_length=2, default="FR")
    available_from = models.DateTimeField(null=True, blank=True, db_index=True)
    view_count = models.PositiveIntegerField(default=0, db_index=True)

    source_type = models.CharField(max_length=12, default="images")  # images|video
    source_video = models.ForeignKey(
        VideoUpload,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listings",
    )
    ai_summary = models.JSONField(default=dict, blank=True)

    shipping_enabled = models.BooleanField(default=True, db_index=True)
    in_person_enabled = models.BooleanField(default=True, db_index=True)
    source_item = models.OneToOneField(
        "ingestion.DetectedItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_listing",
    )
    reserved_for = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reserved_listings",
    )
    reserved_at = models.DateTimeField(null=True, blank=True)
    reservation_note = models.TextField(blank=True)

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["category", "status", "created_at"]),
            models.Index(fields=["city", "status", "created_at"]),
            models.Index(fields=["postal_code", "status", "created_at"]),
        ]

    class PublicStatus(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        RESERVED = "reserved", "Réservée"
        SOLD = "sold", "Vendue"
        ARCHIVED = "archived", "Archivée"

    PUBLIC_STATUS_TONES = {
        PublicStatus.AVAILABLE: "success",
        PublicStatus.RESERVED: "warning",
        PublicStatus.SOLD: "danger",
        PublicStatus.ARCHIVED: "secondary",
    }

    PUBLIC_FEED_STATUSES = {
        Status.PUBLISHED,
        Status.RESERVED,
        Status.RESERVATION_ACCEPTED,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_status = self.status

    def __str__(self):
        return self.title

    def get_primary_image(self):
        primary = (
            self.images.filter(is_primary=True).select_related("image_asset").first()
        )
        if primary:
            return primary
        return self.images.select_related("image_asset").order_by("sort_order").first()

    def cancel_active_reservation(self):
        now = timezone.now()
        active = self.reservations.active()
        if active.exists():
            active.update(cancelled_at=now)

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = slugify(self.title)[:160]
        prev_status = self._initial_status
        super().save(*args, **kwargs)
        if prev_status == self.Status.RESERVED and self.status == self.Status.PUBLISHED:
            self.cancel_active_reservation()
        self._initial_status = self.status

    def refresh_reservation_state(self):
        now = timezone.now()
        stale = self.reservations.filter(cancelled_at__isnull=True, expires_at__lte=now)
        if stale.exists():
            stale.update(cancelled_at=now)
        active = (
            self.reservations.filter(cancelled_at__isnull=True, expires_at__gt=now)
            .select_related("buyer")
            .order_by("-reserved_at")
            .first()
        )
        reserved_states = {
            self.Status.RESERVED,
            self.Status.RESERVATION_ACCEPTED,
        }
        if active and self.status not in reserved_states:
            self.status = self.Status.RESERVED
            self.save(update_fields=["status"])
        if not active and self.status in reserved_states:
            self.status = self.Status.PUBLISHED
            self.save(update_fields=["status"])
        return active

    def increment_view_count(self):
        Listing.objects.filter(pk=self.pk).update(view_count=F("view_count") + 1)
        self.refresh_from_db(fields=["view_count"])

    def get_public_status(self):
        if self.status == self.Status.PUBLISHED:
            return self.PublicStatus.AVAILABLE
        if self.status in {self.Status.RESERVED, self.Status.RESERVATION_ACCEPTED}:
            return self.PublicStatus.RESERVED
        if self.status == self.Status.SOLD:
            return self.PublicStatus.SOLD
        if self.status == self.Status.ARCHIVED:
            return self.PublicStatus.ARCHIVED
        return None

    @property
    def is_reserved_state(self):
        return self.status in {self.Status.RESERVED, self.Status.RESERVATION_ACCEPTED}

    def reservation_badge_label(self, user):
        if not self.is_reserved_state:
            return None
        if user and self.reserved_for_id == getattr(user, "id", None):
            return "Réservé pour vous"
        return "Réservé"

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
            self.PublicStatus.RESERVED,
        }


class ListingView(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listing_views"
    )
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="views")
    viewed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        unique_together = [("user", "listing")]
        indexes = [
            models.Index(fields=["user", "listing"]),
            models.Index(fields=["viewed_at"]),
        ]

    def __str__(self):
        return f"{self.user} viewed {self.listing} at {self.viewed_at}"


class ListingImage(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="images"
    )
    image_asset = models.ForeignKey(
        ImageAsset, on_delete=models.PROTECT, related_name="listing_images"
    )
    keyframe = models.ForeignKey(
        Keyframe,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listing_images",
    )

    is_primary = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["listing", "sort_order"])]


class ReservationQuerySet(models.QuerySet):
    def active(self):
        now = timezone.now()
        return self.filter(cancelled_at__isnull=True, expires_at__gt=now)


class ReservationManager(models.Manager):
    def get_queryset(self):
        return ReservationQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()


class Reservation(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)

    objects = ReservationManager()

    class Meta:
        ordering = ["-reserved_at"]

    def is_active(self):
        return self.cancelled_at is None and self.expires_at > timezone.now()

    def cancel(self):
        if not self.cancelled_at:
            self.cancelled_at = timezone.now()
            self.save(update_fields=["cancelled_at"])


class ReservationLog(models.Model):
    class Action(models.TextChoices):
        RESERVED = "reserved", "Réservé"
        CANCELLED = "cancelled", "Annulé"
        ACCEPTED = "accepted", "Accepté"

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reservation_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservation_logs",
    )
    action = models.CharField(
        max_length=16, choices=Action.choices, db_index=True
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ListingReminder(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_reminders",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="reminders",
    )
    notify_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "listing")]

    def save(self, *args, **kwargs):
        if not self.notify_at:
            available = self.listing.available_from
            if available:
                self.notify_at = available - timedelta(hours=6)
            else:
                self.notify_at = timezone.now()
        super().save(*args, **kwargs)


class SearchAlert(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_alerts",
    )
    keyword = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="search_alerts",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "keyword", "city", "category")]

    def matches(self, listing):
        if listing.seller == self.user:
            return False
        if self.keyword:
            text = f"{listing.title} {listing.description}".lower()
            if self.keyword.lower() not in text:
                return False
        if self.city and self.city.strip():
            if self.city.lower() != listing.city.lower():
                return False
        if self.category and listing.category_id != self.category_id:
            return False
        return True

    def __str__(self):
        parts = [self.keyword or "mot-clé libre"]
        if self.city:
            parts.append(self.city)
        if self.category:
            parts.append(self.category.name)
        return " · ".join(parts)


class SearchAlertNotification(models.Model):
    alert = models.ForeignKey(
        SearchAlert,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="alert_notifications",
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("alert", "listing")]


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "listing")]

