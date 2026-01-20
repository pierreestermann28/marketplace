import re
from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Message


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"(\+?\d[\d\s-]{6,}\d)")
LINK_PATTERN = re.compile(r"(https?://|www\.)", re.IGNORECASE)
RATE_LIMIT_SECONDS = 5


class MessageForm(forms.ModelForm):
    def __init__(self, *args, conversation=None, sender=None, **kwargs):
        self.conversation = conversation
        self.sender = sender
        super().__init__(*args, **kwargs)

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
            raise forms.ValidationError(
                "Merci de ne pas partager de numéro de téléphone."
            )
        if LINK_PATTERN.search(text):
            raise forms.ValidationError("Merci de ne pas poster de liens externes.")
        return text

    def clean(self):
        cleaned = super().clean()
        if self.conversation and self.sender:
            last_message = (
                self.conversation.messages.filter(sender=self.sender)
                .order_by("-created_at")
                .first()
            )
            if last_message:
                elapsed = timezone.now() - last_message.created_at
                if elapsed < timedelta(seconds=RATE_LIMIT_SECONDS):
                    raise forms.ValidationError(
                        "Patientez quelques secondes avant d’envoyer un nouveau message."
                    )
        return cleaned
