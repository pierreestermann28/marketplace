from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "input",
                    "rows": 4,
                    "placeholder": "Décris ton expérience avec cet utilisateur...",
                }
            ),
            "rating": forms.NumberInput(
                attrs={"class": "input", "min": 1, "max": 5, "step": 1}
            ),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating is None:
            return rating
        if rating < 1 or rating > 5:
            raise forms.ValidationError("La note doit être comprise entre 1 et 5.")
        return rating
