from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView, View

from listings.models import Listing
from listings.views import get_listing_detail_url
from messaging.models import Conversation
from .forms import ReportForm
from .models import Report


class _BaseReportCreateView(LoginRequiredMixin, FormView):
    form_class = ReportForm
    template_name = "components/reports/report_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.target = self.get_target()
        return super().dispatch(request, *args, **kwargs)

    def get_target(self):
        raise NotImplementedError

    def form_valid(self, form):
        report = form.save(commit=False)
        report.reporter = self.request.user
        report.target_content_type = ContentType.objects.get_for_model(self.target)
        report.target_object_id = str(self.target.pk)
        report.save()
        self.on_report_created(report)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Impossible d'enregistrer le signalement.")
        return redirect(self.get_success_url())

    def on_report_created(self, report):
        messages.success(self.request, "Merci, nous examinons le signalement.")

    def get_success_url(self):
        raise NotImplementedError


class ListingReportCreateView(_BaseReportCreateView):
    def get_target(self):
        return get_object_or_404(Listing, pk=self.kwargs["listing_id"])

    def get_success_url(self):
        return get_listing_detail_url(self.target)


class ConversationReportCreateView(_BaseReportCreateView):
    def get_target(self):
        conversation = get_object_or_404(
            Conversation.objects.select_related("listing"), pk=self.kwargs["pk"]
        )
        return conversation

    def on_report_created(self, report):
        super().on_report_created(report)

    def get_success_url(self):
        return reverse("messages:detail", kwargs={"pk": self.target.pk})


class ReportingLandingView(TemplateView):
    template_name = "pages/report_help.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_meta"] = {
            "title": "Signaler un contenu · StillUseful",
            "description": "Guide des signalements pour annonces ou conversations et étapes pour régler un litige.",
        }
        return context
