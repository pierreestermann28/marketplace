from django import forms
from django.core.exceptions import ValidationError

from .models import Listing


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            "title",
            "category",
            "description",
            "condition",
            "price_cents",
            "currency",
            "postal_code",
            "city",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"class": "textarea"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"category", "condition", "currency"}:
                field.widget.attrs["class"] = "input"
            elif name == "description":
                field.widget = forms.Textarea(attrs={"class": "textarea"})
            else:
                field.widget.attrs["class"] = "input"


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        return files.getlist(name)


class MultiFileField(forms.Field):
    widget = MultiFileInput
    default_error_messages = {"required": "Veuillez ajouter au moins une photo."}

    def clean(self, value):
        value = super().clean(value)
        files = value or []
        if not files:
            raise ValidationError(self.error_messages["required"])
        return files


class PhotoUploadForm(forms.Form):
    images = MultiFileField(required=True, widget=MultiFileInput(attrs={"multiple": True}))
