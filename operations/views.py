from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from billing.models import UserEntitlement
from commerce.models import Dispute, Order
from ingestion.models import DetectedItem
from listings.models import Listing
from ingestion.models import BatchUpload
from reports.models import Report

from ingestion.views import _build_admin_counts, _get_next_admin_item


class ReviewActionMixin:
    def _handle_review_action(self, request):
        action = request.POST.get("action")
        listing_id = request.POST.get("listing_id")
        listing = get_object_or_404(Listing, pk=listing_id)
        if action == "approve":
            listing.status = Listing.Status.PUBLISHED
            listing.moderation_notes = ""
            listing.needs_review = False
            listing.moderated_by = request.user
            listing.moderated_at = timezone.now()
            listing.save(
                update_fields=[
                    "status",
                    "moderation_notes",
                    "moderated_by",
                    "moderated_at",
                    "needs_review",
                ]
            )
            listing.record_history(
                request.user,
                Listing.ChangeEvent.APPROVED,
                "Annonce validée depuis la file de modération.",
            )
            messages.success(
                request,
                f"L'annonce «{listing.title or listing.id}» est validée et repasse en ligne.",
            )
        elif action == "reject":
            note = request.POST.get("note", "").strip()
            listing.status = Listing.Status.REJECTED
            listing.moderation_notes = note
            listing.needs_review = False
            listing.moderated_by = request.user
            listing.moderated_at = timezone.now()
            listing.save(
                update_fields=[
                    "status",
                    "moderation_notes",
                    "moderated_by",
                    "moderated_at",
                    "needs_review",
                ]
            )
            listing.record_history(
                request.user,
                Listing.ChangeEvent.REJECTED,
                f"Annonce rejetée depuis la file ({note or 'sans motif'}).",
            )
            messages.success(
                request, f"L'annonce «{listing.title or listing.id}» est refusée."
            )
        else:
            messages.error(request, "Action inconnue.")
        return redirect(self._return_url())

    def _return_url(self):
        return reverse("operations:dashboard")


class OperationsDashboardView(UserPassesTestMixin, TemplateView):
    template_name = "operations/admin_workroom.html"

    def test_func(self):
        return self.request.user.is_staff

    def _get_operation_counts(self):
        return {
            "orders_pending": Order.objects.filter(
                status__in=[Order.Status.CREATED, Order.Status.AWAITING_CONFIRMATION]
            ).count(),
            "orders_attention": Order.objects.filter(
                status__in=[
                    Order.Status.DISPUTE,
                    Order.Status.EXPIRED,
                    Order.Status.CANCELLED,
                ]
            ).count(),
            "open_disputes": Dispute.objects.filter(is_resolved=False).count(),
            "pending_detected_items": DetectedItem.objects.filter(
                status=DetectedItem.Status.PENDING
            ).count(),
            "trending_listings": (
                Listing.objects.filter(status=Listing.Status.PUBLISHED)
                .order_by("-view_count")
                .select_related("seller")
                .prefetch_related("images")
                .all()[:6]
            ),
        }

    def _get_recent_batch_summaries(self):
        batches = (
            BatchUpload.objects.select_related("owner")
            .order_by("-created_at")
            .all()[:5]
        )
        if not batches:
            return []
        batch_ids = [batch.id for batch in batches]
        counts = self._batch_detected_counts(batch_ids)
        summaries = []
        for batch in batches:
            stats = counts.get(batch.id, {})
            ready = stats.get(DetectedItem.Status.USER_APPROVED, 0) + stats.get(
                DetectedItem.Status.ADMIN_APPROVED, 0
            )
            pending = stats.get(DetectedItem.Status.PENDING, 0)
            others = sum(
                value
                for status, value in stats.items()
                if status
                not in {
                    DetectedItem.Status.PENDING,
                    DetectedItem.Status.USER_APPROVED,
                    DetectedItem.Status.ADMIN_APPROVED,
                }
            )
            summaries.append(
                {
                    "batch": batch,
                    "pending": pending,
                    "ready": ready,
                    "others": others,
                    "total_detected": sum(stats.values()),
                }
            )
        return summaries

    def _batch_detected_counts(self, batch_ids):
        if not batch_ids:
            return {}
        data = (
            DetectedItem.objects.filter(batch_id__in=batch_ids)
            .values("batch_id", "status")
            .annotate(count=Count("id"))
        )
        counts = defaultdict(dict)
        for entry in data:
            counts[entry["batch_id"]][entry["status"]] = entry["count"]
        return counts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._get_operation_counts())
        context.update(_build_admin_counts())
        context["current_item"] = _get_next_admin_item()
        context["pending_review_listings"] = (
            Listing.objects.filter(
                Q(status=Listing.Status.PENDING_REVIEW) | Q(needs_review=True)
            )
            .select_related("seller", "category")
            .order_by("created_at")[:6]
        )
        context["batch_summaries"] = self._get_recent_batch_summaries()
        context["premium_entitlements"] = self._get_recent_entitlements()
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "toggle_premium":
            return self._handle_premium_toggle(request)
        return ReviewActionMixin._handle_review_action(self, request)

    def _get_recent_entitlements(self):
        return (
            UserEntitlement.objects.select_related("user")
            .order_by("-updated_at")
            .all()[:6]
        )

    def _handle_premium_toggle(self, request):
        user_id = request.POST.get("user_id")
        mode = request.POST.get("mode")
        entitlement = get_object_or_404(
            UserEntitlement.objects.select_related("user"), user__id=user_id
        )
        if mode == "enable":
            entitlement.is_premium = True
            entitlement.premium_until = None
            message = f"Premium activé pour {entitlement.user.get_full_name() or entitlement.user.email}."
        else:
            entitlement.is_premium = False
            entitlement.premium_until = None
            message = f"Premium suspendu pour {entitlement.user.get_full_name() or entitlement.user.email}."
        entitlement.save(update_fields=["is_premium", "premium_until", "updated_at"])
        messages.success(request, message)
        return redirect(self._return_url())


class AdminListingModerationView(UserPassesTestMixin, TemplateView):
    template_name = "moderation/admin_listings.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        status_filter = self.request.GET.get("status")
        valid_statuses = {value for value, _ in Listing.Status.choices}
        qs = (
            Listing.objects.select_related("seller")
            .prefetch_related("reports", "images")
            .order_by("-updated_at")
        )
        if status_filter in valid_statuses:
            qs = qs.filter(status=status_filter)
        return qs[:60]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status_counts = Listing.objects.values("status").annotate(count=Count("id"))
        counts_map = {entry["status"]: entry["count"] for entry in status_counts}
        context.update(
            {
                "listings": self.get_queryset(),
                "reports": Report.objects.filter(is_resolved=False)
                .select_related("listing__seller", "reporter")
                .order_by("-created_at")[:12],
                "status_filter": self.request.GET.get("status") or "",
                "status_choices_for_filter": [
                    {
                        "value": value,
                        "label": label,
                        "count": counts_map.get(value, 0),
                    }
                    for value, label in Listing.Status.choices
                ],
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        listing_id = request.POST.get("listing_id")
        listing = get_object_or_404(
            Listing.objects.select_related("seller"), pk=listing_id
        )
        if action == "unpublish":
            note = request.POST.get("note", "").strip()
            listing.status = Listing.Status.ARCHIVED
            fields = ["status", "moderated_by", "moderated_at"]
            listing.moderated_by = request.user
            listing.moderated_at = timezone.now()
            if note:
                listing.moderation_notes = note
                fields.append("moderation_notes")
            listing.save(update_fields=fields)
            listing.record_history(
                request.user,
                Listing.ChangeEvent.STATUS_UPDATED,
                "Annonce retirée manuellement par l’équipe.",
            )
            messages.success(
                request,
                f"L'annonce «{listing.title or listing.id}» est hors ligne.",
            )
        elif action == "ban_user":
            seller = listing.seller
            seller.is_active = False
            seller.save(update_fields=["is_active"])
            messages.success(
                request,
                f"L'utilisateur {seller.get_full_name() or seller.email} est désactivé.",
            )
        elif action == "approve":
            listing.status = Listing.Status.PUBLISHED
            listing.moderation_notes = ""
            listing.moderated_by = request.user
            listing.moderated_at = timezone.now()
            listing.needs_review = False
            listing.save(
                update_fields=[
                    "status",
                    "moderation_notes",
                    "moderated_by",
                    "moderated_at",
                    "needs_review",
                ]
            )
            messages.success(
                request,
                f"L'annonce «{listing.title or listing.id}» est validée et repasse en ligne.",
            )
            listing.record_history(
                request.user,
                Listing.ChangeEvent.APPROVED,
                "Annonce validée depuis l’administration.",
            )
        elif action == "reject":
            note = request.POST.get("note", "").strip()
            listing.status = Listing.Status.REJECTED
            listing.moderation_notes = note
            listing.moderated_by = request.user
            listing.moderated_at = timezone.now()
            listing.needs_review = False
            listing.save(
                update_fields=[
                    "status",
                    "moderation_notes",
                    "moderated_by",
                    "moderated_at",
                    "needs_review",
                ]
            )
            messages.success(
                request,
                f"L'annonce «{listing.title or listing.id}» est refusée.",
            )
            listing.record_history(
                request.user,
                Listing.ChangeEvent.REJECTED,
                f"Annonce refusée par l’équipe ({note or 'sans motif'}).",
            )
            listing.needs_review = False
            listing.save(update_fields=["needs_review"])
        else:
            messages.error(request, "Action inconnue.")
        return redirect(self._return_url())

    def _return_url(self):
        base = reverse("operations:admin_listings")
        query = self.request.GET.urlencode()
        return f"{base}?{query}" if query else base
