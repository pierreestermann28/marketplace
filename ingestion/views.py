import json

from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from mediahub.services import create_image_asset
from ingestion.models import BatchUpload, BatchMedia

from .forms import BatchUploadForm
from .models import DetectedItem
from billing.entitlements import QuotaExceeded
from .tasks import analyze_batch
from .services import batches, items, publishing, queries

BATCH_STUCK_THRESHOLD_SECONDS = getattr(settings, "BATCH_STUCK_THRESHOLD_SECONDS", 600)


def _is_batch_stuck(batch):
    if batch.status != BatchUpload.Status.RUNNING or not batch.processing_started_at:
        return False
    return (
        timezone.now() - batch.processing_started_at
    ).total_seconds() > BATCH_STUCK_THRESHOLD_SECONDS


def _batch_status_hint(batch, is_stuck, progress):
    if batch.status == BatchUpload.Status.PENDING:
        return "Traitement programmé. Préparez-vous à voir vos cartes."
    if batch.status == BatchUpload.Status.RUNNING:
        if is_stuck:
            return "L’analyse semble bloquée. Vous pouvez la relancer."
        return f"Analyse en cours ({progress}%)."
    if batch.status == BatchUpload.Status.DONE:
        return "Analyse terminée. Vous pouvez passer au swipe."
    if batch.status == BatchUpload.Status.FAILED:
        return batch.error_message or "Une erreur est survenue. Relancez l’analyse."
    return ""


def _build_batch_status_context(batch):
    pending_count = batch.detected_items.filter(
        status=DetectedItem.Status.PENDING
    ).count()
    detected_count = batch.detected_items.count()
    progress = batches.progress_percentage(batch=batch)
    is_stuck = _is_batch_stuck(batch)
    return {
        "batch": batch,
        "pending_count": pending_count,
        "detected_count": detected_count,
        "progress": progress,
        "is_stuck": is_stuck,
        "status_hint": _batch_status_hint(batch, is_stuck, progress),
        "can_retry": batch.status in {BatchUpload.Status.FAILED} or is_stuck,
    }


class BatchOwnerMixin(LoginRequiredMixin):
    batch_kwarg = "batch_id"

    def get_batch(self):
        if not hasattr(self, "_batch"):
            self._batch = get_object_or_404(
                BatchUpload,
                id=self.kwargs[self.batch_kwarg],
                owner=self.request.user,
            )
        return self._batch

    def get_pending_items(self, batch):
        return batch.detected_items.filter(status=DetectedItem.Status.PENDING)

    def get_next_item(self, batch):
        return (
            self.get_pending_items(batch)
            .select_related("hero_asset__image_asset")
            .order_by("created_at")
            .first()
        )


class BatchUploadCreateView(LoginRequiredMixin, FormView):
    template_name = "ingestion/upload.html"
    form_class = BatchUploadForm

    def form_valid(self, form):
        files = form.cleaned_data["media_files"]
        batch = BatchUpload.objects.create(
            owner=self.request.user,
            media_count=len(files),
        )
        batch.sale_location = form.cleaned_data.get("sale_location", "") or ""
        batch.seller_notes = form.cleaned_data.get("seller_notes", "") or ""
        batch.save(update_fields=["sale_location", "seller_notes"])
        for upload in files:
            image_asset = create_image_asset(user=self.request.user, image=upload)
            BatchMedia.objects.create(batch=batch, image_asset=image_asset)
        analyze_batch.delay(str(batch.id))
        return redirect("ingestion:batch_processing", batch_id=batch.id)


class BatchProcessingView(BatchOwnerMixin, TemplateView):
    template_name = "ingestion/processing.html"

    def get_context_data(self, **kwargs):
        batch = self.get_batch()
        context = super().get_context_data(**kwargs)
        context.update(_build_batch_status_context(batch))
        return context


class BatchStatusFragmentView(BatchOwnerMixin, TemplateView):
    template_name = "fragments/ingestion/processing_status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        batch = self.get_batch()
        context.update(_build_batch_status_context(batch))
        return context


class BatchProcessingRetryView(BatchOwnerMixin, View):
    def post(self, request, *args, **kwargs):
        batch = self.get_batch()
        stuck = _is_batch_stuck(batch)
        if batch.status == BatchUpload.Status.RUNNING and not stuck:
            django_messages.info(
                request,
                "Le traitement est déjà lancé. Patientez ou attendez la fin.",
            )
        else:
            batches.reset_for_retry(batch=batch)
            analyze_batch.delay(str(batch.id))
            django_messages.success(
                request,
                "Analyse relancée. Les résultats seront disponibles sous peu.",
            )
        context = _build_batch_status_context(batch)
        if request.headers.get("HX-Request"):
            return render(
                request, "fragments/ingestion/processing_status.html", context
            )
        return redirect("ingestion:batch_processing", batch_id=batch.id)


class BatchSwipeView(BatchOwnerMixin, TemplateView):
    template_name = "ingestion/swipe.html"

    def get_context_data(self, **kwargs):
        batch = self.get_batch()
        context = super().get_context_data(**kwargs)
        context["batch"] = batch
        context["current_item"] = self.get_next_item(batch)
        context["pending_count"] = self.get_pending_items(batch).count()
        context["approved_count"] = batch.detected_items.filter(
            status=DetectedItem.Status.USER_APPROVED
        ).count()
        context["rejected_count"] = batch.detected_items.filter(
            status=DetectedItem.Status.USER_REJECTED
        ).count()
        context["items"] = list(self.get_pending_items(batch)[:SWIPE_PREFETCH_LIMIT])
        return context


def _render_swipe_fragment(request, item):
    if item:
        return render(
            request, "fragments/ingestion/swipe_card.html", {"current_item": item}
        )
    return render(request, "fragments/ingestion/swipe_empty.html")


SWIPE_PREFETCH_LIMIT = 3


class SwipeListView(LoginRequiredMixin, TemplateView):
    template_name = "ingestion/swipe.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pending_qs = queries.get_user_pending_items(self.request.user)
        items = list(pending_qs[:SWIPE_PREFETCH_LIMIT])
        context["items"] = items
        context["pending_count"] = pending_qs.count()
        return context


class SwipeNextCardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        next_item = queries.get_next_user_item(request.user)
        return _render_swipe_fragment(request, next_item)


class SwipeDecisionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            payload = request.POST
        item_id = payload.get("item_id")
        decision = payload.get("decision")
        if not item_id or decision not in {"keep", "reject", "snooze"}:
            return HttpResponseBadRequest("Décision invalide")
        item = get_object_or_404(DetectedItem, id=item_id, owner=request.user)
        if item.status != DetectedItem.Status.PENDING:
            return HttpResponse(status=409)
        if decision == "keep":
            items.user_approve(item=item)
        elif decision == "reject":
            items.user_reject(item=item)
        else:
            item.status = DetectedItem.Status.EDITED
            item.save(update_fields=["status", "updated_at"])
        next_item = queries.get_next_user_item(request.user)
        html = ""
        empty = True
        if next_item:
            html = render_to_string(
                "fragments/ingestion/swipe_deck_card.html",
                {"item": next_item},
                request=request,
            )
            empty = False
        else:
            html = render_to_string(
                "fragments/ingestion/swipe_empty.html", request=request
            )
        return HttpResponse(
            json.dumps({"html": html, "empty": empty}),
            content_type="application/json",
        )


def _render_swipe_fragment(request, item):
    if item:
        return render(
            request, "fragments/ingestion/swipe_card.html", {"current_item": item}
        )
    return render(request, "fragments/ingestion/swipe_empty.html")


class DetectedItemActionMixin(LoginRequiredMixin):
    item_kwarg = "item_id"

    def get_item(self):
        return get_object_or_404(
            DetectedItem.objects.select_related("batch", "hero_asset__image_asset"),
            id=self.kwargs[self.item_kwarg],
            owner=self.request.user,
        )

    def get_next_item(self, batch):
        return (
            batch.detected_items.filter(status=DetectedItem.Status.PENDING)
            .select_related("hero_asset__image_asset")
            .order_by("created_at")
            .first()
        )

    def render_next_card(self, request, batch):
        next_item = self.get_next_item(batch)
        if next_item:
            return render(
                request,
                "fragments/ingestion/swipe_card.html",
                {"batch": batch, "current_item": next_item},
            )
        return render(
            request,
            "fragments/ingestion/swipe_empty.html",
            {"batch": batch},
        )


class DetectedItemApproveView(DetectedItemActionMixin, View):
    def post(self, request, *args, **kwargs):
        item = self.get_item()
        if item.status != DetectedItem.Status.PENDING:
            return self.render_next_card(request, item.batch)

        with transaction.atomic():
            items.user_approve(item=item)
        return self.render_next_card(request, item.batch)


class DetectedItemRejectView(DetectedItemActionMixin, View):
    def post(self, request, *args, **kwargs):
        item = self.get_item()
        if item.status != DetectedItem.Status.PENDING:
            return self.render_next_card(request, item.batch)
        items.user_reject(item=item)
        return self.render_next_card(request, item.batch)


class AdminSwipeView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        return redirect("operations:dashboard")


class AdminSwipeFragmentView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        next_item = queries.get_next_admin_item()
        context = queries.get_admin_counts()
        context["current_item"] = next_item
        template = (
            "fragments/ingestion/admin_swipe_card.html"
            if next_item
            else "fragments/ingestion/admin_swipe_empty.html"
        )
        return render(request, template, context)


class DetectedItemAdminActionMixin(DetectedItemActionMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

    def get_item(self):
        return get_object_or_404(
            DetectedItem.objects.select_related("batch", "hero_asset__image_asset"),
            id=self.kwargs[self.item_kwarg],
        )

    def render_admin_card(self, request):
        next_item = queries.get_next_admin_item()
        context = queries.get_admin_counts()
        context["current_item"] = next_item
        template = (
            "fragments/ingestion/admin_swipe_card.html"
            if next_item
            else "fragments/ingestion/admin_swipe_empty.html"
        )
        return render(request, template, context)


class DetectedItemAdminApproveView(DetectedItemAdminActionMixin, View):
    def post(self, request, *args, **kwargs):
        item = self.get_item()
        if item.status != DetectedItem.Status.USER_APPROVED:
            return self.render_admin_card(request)

        try:
            with transaction.atomic():
                listing = publish_detected_item(item, skip_quota=True)
                item.listing = listing
                item.save(update_fields=["listing"])
                items.admin_approve(item=item)
        except QuotaExceeded as exc:
            return _render_quota_prompt(request, item, str(exc))
        return self.render_admin_card(request)


class DetectedItemAdminRejectView(DetectedItemAdminActionMixin, View):
    def post(self, request, *args, **kwargs):
        item = self.get_item()
        if item.status != DetectedItem.Status.USER_APPROVED:
            return self.render_admin_card(request)
        items.admin_reject(item=item)
        return self.render_admin_card(request)


def _render_quota_prompt(request, item, message):
    context = queries.get_admin_counts()
    context["current_item"] = item
    context["quota_error_message"] = message
    context["upgrade_url"] = getattr(settings, "PREMIUM_UPGRADE_URL", "/pricing")
    return render(request, "fragments/ingestion/quota_upgrade.html", context)
