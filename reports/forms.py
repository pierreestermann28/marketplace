from django import forms

from .models import Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reason", "details"]
        widgets = {
            "reason": forms.Select(
                attrs={
                    "class": "input",
                    "id": "report-reason",
                }
            ),
            "details": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 3,
                    "id": "report-details",
                    "placeholder": "Ajoute un contexte (facultatif)...",
                }
            ),
        }
