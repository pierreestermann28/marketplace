from django.shortcuts import get_object_or_404

from listings.models import Listing
from listings.views import get_listing_detail_url

from .base import _BaseReportCreateView


class ListingReportCreateView(_BaseReportCreateView):
    def get_target(self):
        return get_object_or_404(Listing, pk=self.kwargs["listing_id"])

    def get_success_url(self):
        return get_listing_detail_url(self.target)
