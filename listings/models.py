import uuid
from django.conf import settings
from django.db import models
from catalog.models import Category
from media.models import ImageAsset, VideoUpload, Keyframe
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
        Category, on_delete=models.PROTECT, related_name="listings"
    )

    title = models.CharField(max_length=140, db_index=True)
    slug = models.SlugField(max_length=160, blank=True, db_index=True)
    description = models.TextField(blank=True)
    condition = models.CharField(
        max_length=16, choices=Condition.choices, default=Condition.GOOD, db_index=True
    )

    price_cents = models.PositiveIntegerField(db_index=True)
    currency = models.CharField(max_length=3, default="EUR")

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )

    postal_code = models.CharField(max_length=20, db_index=True)
    city = models.CharField(max_length=80, db_index=True)
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

    def __str__(self):
        return self.title


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

    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["listing", "sort_order"])]


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
