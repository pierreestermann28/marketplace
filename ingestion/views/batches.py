from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from mediahub.services import create_image_asset

from ingestion.forms import BatchUploadForm
from ingestion.models import BatchMedia, BatchUpload, DetectedItem
from ingestion.services import batches
from ingestion.tasks import analyze_batch
from ingestion.views.constants import SWIPE_PREFETCH_LIMIT

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
        batch = self.get_batch()
        context = super().get_context_data(**kwargs)
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
