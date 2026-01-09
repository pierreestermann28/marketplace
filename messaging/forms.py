import re

from django import forms
from django.utils import timezone

from .models import Message


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"(\+?\d[\d\s-]{6,}\d)")


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "class": "input",
                    "rows": 3,
                    "placeholder": "Écrivez votre message ici...",
                }
            ),
        }

    def clean_text(self):
        text = self.cleaned_data.get("text", "").strip()
        if EMAIL_PATTERN.search(text):
            raise forms.ValidationError("Merci de ne pas partager d’e-mail.")
        if PHONE_PATTERN.search(text):
            raise forms.ValidationError("Merci de ne pas partager de numéro de téléphone.")
        return text
