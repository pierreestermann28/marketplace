from django.shortcuts import render

from listings.views.public import HomeFeedView


class HomeFeedPartialView(HomeFeedView):
    template_name = "fragments/home/listings_feed.html"
    paginate_by = 24
    context_object_name = "listings"

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return render(request, self.get_template_names(), context)
