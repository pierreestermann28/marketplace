from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView

from reports.forms import ReportForm
from reports.services.create import AlreadyReportedError, create_report


class _BaseReportCreateView(LoginRequiredMixin, FormView):
    template_name = "components/reports/report_form.html"
    form_class = ReportForm

    def dispatch(self, request, *args, **kwargs):
        self.target = self.get_target()
        return super().dispatch(request, *args, **kwargs)

    def get_target(self):
        raise NotImplementedError

    def form_valid(self, form):
        try:
            report = create_report(
                reporter=self.request.user,
                target=self.target,
                reason=form.cleaned_data["reason"],
                details=form.cleaned_data.get("details", ""),
            )
        except AlreadyReportedError:
            messages.info(
                self.request,
                "Vous avez déjà signalé cet élément. Nous traitons votre demande.",
            )
            return redirect(self.get_success_url())

        self.on_report_created(report)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Impossible d'enregistrer le signalement.")
        return redirect(self.get_success_url())

    def on_report_created(self, target):
        messages.success(self.request, "Merci, nous examinons le signalement.")

    def get_success_url(self):
        raise NotImplementedError
