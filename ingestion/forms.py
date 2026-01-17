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
    sale_location = forms.CharField(
        required=False,
        label="Lieu de vente",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ex : Lyon, boutique Le Comptoir, pop-up Paris",
                "class": "input w-full",
                "data-location-city-input": "true",
            }
        ),
        help_text="L’indication principale du lieu ou de la ville ciblée.",
    )
    seller_notes = forms.CharField(
        required=False,
        label="Contexte rapide",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Mentionnez marque, matériaux, état ou tout autre élément utile.",
                "class": "input w-full",
            }
        ),
        help_text="Quelques mots pour guider l'IA.",
    )
