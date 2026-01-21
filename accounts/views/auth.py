from django.contrib import messages
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic import FormView

from accounts.forms import SignUpForm
from accounts.services.users import create_user_from_signup


class SignUpView(FormView):
    template_name = "registration/register.html"
    form_class = SignUpForm
    success_url = reverse_lazy("onboarding")

    def form_valid(self, form):
        user = create_user_from_signup(form=form)
        messages.success(self.request, "Bienvenue ! Ton compte a été créé.")
        login(self.request, user)
        return super().form_valid(form)
