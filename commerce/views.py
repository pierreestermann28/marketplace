from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView

from .forms import ReviewForm
from .models import Order, Review


class ReviewCreateView(LoginRequiredMixin, FormView):
    template_name = "reviews/review_form.html"
    form_class = ReviewForm

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(Order, id=kwargs["order_id"])
        self.role = kwargs["role"]
        if self.order.status != Order.Status.COMPLETED:
            raise PermissionDenied("La commande n'est pas terminée.")
        if self.role not in (Review.Role.BUYER_TO_SELLER, Review.Role.SELLER_TO_BUYER):
            raise PermissionDenied()
        if self.role == Review.Role.BUYER_TO_SELLER and request.user != self.order.buyer:
            raise PermissionDenied()
        if self.role == Review.Role.SELLER_TO_BUYER and request.user != self.order.seller:
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        target = self.order.seller if self.role == Review.Role.BUYER_TO_SELLER else self.order.buyer
        Review.objects.update_or_create(
            order=self.order,
            role=self.role,
            defaults={
                "author": self.request.user,
                "target": target,
                "rating": form.cleaned_data["rating"],
                "comment": form.cleaned_data.get("comment", "").strip(),
            },
        )
        stats = target.reputation
        stats.rebuild_from_reviews()
        return redirect(
            reverse(
                "listing_detail",
                kwargs={"slug": self.order.listing.slug or "item", "uuid": self.order.listing.id},
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order"] = self.order
        context["role"] = self.role
        context["target_user"] = (
            self.order.seller if self.role == Review.Role.BUYER_TO_SELLER else self.order.buyer
        )
        return context
