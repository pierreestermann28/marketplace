from django import forms

from listings.forms import MultiFileField, MultiFileInput


class BatchUploadForm(forms.Form):
    media_files = MultiFileField(
        required=True,
        min_count=1,
        max_count=30,
        widget=MultiFileInput(attrs={"multiple": True}),
        label="Photos (1 à 30 fichiers)",
    )
