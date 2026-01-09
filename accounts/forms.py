from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class SignUpForm(UserCreationForm):
    username = forms.CharField(label="Identifiant", widget=forms.TextInput(attrs={"autocomplete": "username"}))
    email = forms.EmailField(
        label="Adresse email",
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    first_name = forms.CharField(
        label="Prénom",
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        label="Nom",
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )
    password1 = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmation du mot de passe", widget=forms.PasswordInput)

    class Meta:
        model = get_user_model()
        fields = ["username", "email", "first_name", "last_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if "class" not in field.widget.attrs:
                field.widget.attrs["class"] = "input"
            else:
                field.widget.attrs["class"] += " input"
            if field_name in {"username", "email"}:
                field.widget.attrs.setdefault("autocomplete", field_name)
            if field_name in {"password1", "password2"}:
                field.help_text = ""
