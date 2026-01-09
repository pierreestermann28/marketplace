import uuid
from django.conf import settings
from django.db import models
from catalog.models import Category
from django.db.models import Prefetch

from mediahub.models import ImageAsset, VideoUpload, Keyframe
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class Listing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PENDING_REVIEW = "pending_review"
        PUBLISHED = "published"
        REJECTED = "rejected"
        RESERVED = "reserved"
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["category", "status", "created_at"]),
            models.Index(fields=["city", "status", "created_at"]),
            models.Index(fields=["postal_code", "status", "created_at"]),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_status = self.status

    def __str__(self):
        return self.title

    def get_primary_image(self):
        primary = self.images.filter(is_primary=True).select_related("image_asset").first()
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
        if active and self.status != self.Status.RESERVED:
            self.status = self.Status.RESERVED
            self.save(update_fields=["status"])
        if not active and self.status == self.Status.RESERVED:
            self.status = self.Status.PUBLISHED
            self.save(update_fields=["status"])
        return active


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


class Report(models.Model):
    class Reason(models.TextChoices):
        SCAM = "scam"
        ILLEGAL = "illegal"
        INAPPROPRIATE = "inappropriate"
        SPAM = "spam"
        OTHER = "other"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made"
    )
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reports"
    )
    reason = models.CharField(max_length=20, choices=Reason.choices, db_index=True)
    details = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
