# listings/models.py (V2) - models "purs"
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q
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
        """
        Read-only UX helper.
        (Offer detection uses QuerySet.active() which is stable.)
        """
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


class ListingChangeLog(models.Model):
    class ActorRole(models.TextChoices):
        SELLER = "seller", "Vendeur"
        ADMIN = "admin", "Admin"
        SYSTEM = "system", "Système"

    listing = models.ForeignKey(
        "Listing", on_delete=models.CASCADE, related_name="change_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    actor_role = models.CharField(
        max_length=16, choices=ActorRole.choices, default=ActorRole.SELLER
    )
    event = models.CharField(max_length=24, choices=Listing.ChangeEvent.choices)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_event_display()} ({self.listing_id})"


class ListingView(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listing_views"
    )
    listing = models.ForeignKey(
        "Listing", on_delete=models.CASCADE, related_name="views"
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


class ListingImage(models.Model):
    listing = models.ForeignKey(
        "Listing", on_delete=models.CASCADE, related_name="images"
    )
    image_asset = models.ForeignKey(
        "mediahub.ImageAsset", on_delete=models.PROTECT, related_name="listing_images"
    )
    keyframe = models.ForeignKey(
        "mediahub.Keyframe",
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


class OfferQuerySet(models.QuerySet):
    def active(self):
        now = timezone.now()
        return self.filter(
            status="requested",
            cancelled_at__isnull=True,
            expires_at__gt=now,
        )

    def expired(self):
        now = timezone.now()
        return self.filter(
            status="requested",
            cancelled_at__isnull=True,
            expires_at__lte=now,
        )


class Offer(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Offre envoyée"
        ACCEPTED = "accepted", "Offre acceptée"
        REJECTED = "rejected", "Offre refusée"
        CANCELLED = "cancelled", "Offre annulée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="offers"
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offers"
    )

    offer_price_cents = models.PositiveIntegerField(db_index=True)
    currency = models.CharField(max_length=3, default="EUR")

    note = models.TextField(blank=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.REQUESTED, db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)

    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="offers_decided",
    )

    objects = OfferQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["listing", "status", "expires_at"]),
            models.Index(fields=["buyer", "status", "expires_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "buyer"], name="uniq_offer_per_buyer_listing"
            ),
            models.UniqueConstraint(
                fields=["listing"],
                condition=Q(status="accepted", cancelled_at__isnull=True),
                name="uniq_accepted_offer_per_listing",
            ),
        ]

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def is_active(self) -> bool:
        return (
            self.status == self.Status.REQUESTED
            and self.cancelled_at is None
            and not self.is_expired()
        )


class OfferLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Offre créée"
        CANCELLED = "cancelled", "Offre annulée"
        ACCEPTED = "accepted", "Offre acceptée"
        REJECTED = "rejected", "Offre refusée"

    offer = models.ForeignKey(
        "listings.Offer", on_delete=models.CASCADE, related_name="logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offer_logs"
    )

    action = models.CharField(max_length=16, choices=Action.choices, db_index=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["offer", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} ({self.offer_id})"


class ListingReminder(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_reminders",
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="reminders"
    )

    notify_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"], name="uniq_listing_reminder_user_listing"
            ),
        ]


class SearchAlert(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_alerts",
    )
    keyword = models.CharField(max_length=255, blank=True)
    location_city = models.ForeignKey(
        "location.City",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="search_alerts",
    )
    category = models.ForeignKey(
        "catalog.Category",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="search_alerts",
    )

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "keyword", "location_city", "category"],
                name="uniq_search_alert",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active", "created_at"]),
        ]

    def __str__(self):
        parts = [self.keyword or "mot-clé libre"]
        if self.location_city:
            parts.append(self.location_city.name)
        if self.category:
            parts.append(self.category.name)
        return " · ".join(parts)


class SearchAlertNotification(models.Model):
    alert = models.ForeignKey(
        "listings.SearchAlert", on_delete=models.CASCADE, related_name="notifications"
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="alert_notifications"
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["alert", "listing"], name="uniq_search_alert_notification"
            ),
        ]


class OnboardingProfile(models.Model):
    PURPOSE_CHOICES = [
        ("buy", "Acheter"),
        ("sell", "Vendre"),
        ("both", "Acheter & Vendre"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="onboarding_profile",
    )
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES, default="buy")

    location_city = models.ForeignKey(
        "location.City",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="onboarding_profiles",
    )
    radius_km = models.PositiveIntegerField(null=True, blank=True)
    categories = models.ManyToManyField(
        "catalog.Category",
        blank=True,
        related_name="onboarding_profiles",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OnboardingProfile({getattr(self.user, 'email', self.user_id)})"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"], name="uniq_favorite_user_listing"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["listing", "created_at"]),
        ]
