from django.http import HttpResponse
from django.urls import reverse
from django.utils.text import slugify
from django.views import View

from catalog.models import Category
from listings.models import Listing
from listings.views import get_listing_detail_url


class SitemapView(View):
    def get(self, request):
        statuses = [
            Listing.Status.PUBLISHED,
            Listing.Status.RESERVED,
            Listing.Status.RESERVATION_ACCEPTED,
        ]
        listings = (
            Listing.objects.filter(status__in=statuses)
            .order_by("-updated_at")[:1000]
        )
        category_paths = Category.objects.filter(
            listings__status__in=statuses
        ).distinct()
        city_rows = (
            Listing.objects.filter(status__in=statuses)
            .exclude(city__exact="")
            .values_list("city", flat=True)
            .distinct()[:12]
        )

        urls = [
            request.build_absolute_uri(reverse("home")),
        ]
        for category in category_paths:
            urls.append(request.build_absolute_uri(reverse("category_listings", kwargs={"slug": category.slug})))
        for city in city_rows:
            urls.append(request.build_absolute_uri(reverse("city_listings", kwargs={"slug": slugify(city)})))

        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for path in urls:
            lines.append("  <url>")
            lines.append(f"    <loc>{path}</loc>")
            lines.append("  </url>")
        for listing in listings:
            url = request.build_absolute_uri(get_listing_detail_url(listing))
            lines.append("  <url>")
            lines.append(f"    <loc>{url}</loc>")
            lines.append(f"    <lastmod>{listing.updated_at.date().isoformat()}</lastmod>")
            lines.append("  </url>")
        lines.append("</urlset>")
        return HttpResponse("\n".join(lines), content_type="application/xml")
