from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, TemplateView

from .forms import SignUpForm

from .models import ReputationStats, User


class PersonalProfileView(TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        stats = getattr(user, "reputation", None)
        if not stats:
            stats = ReputationStats.for_user(user)
        context.update(
            {
                "object": user,
                "reputation_stats": stats,
                "reviews_received": user.reviews_received.select_related("order__listing")
                .order_by("-created_at")[:5],
            }
        )
        return context

class PublicProfileView(DetailView):
    model = User
    template_name = "accounts/public_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        stats = getattr(user, "reputation", None)
        if not stats:
            stats = ReputationStats.for_user(user)
        context["reputation_stats"] = stats
        context["reviews_received"] = user.reviews_received.select_related("order__listing").order_by("-created_at")[:5]
        return context


class SignUpView(FormView):
    template_name = "registration/register.html"
    form_class = SignUpForm
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, "Bienvenue ! Ton compte a été créé.")
        login(self.request, user)
        return super().form_valid(form)
