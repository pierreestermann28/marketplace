from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.text import slugify
from django.views import View

import redis

from catalog.services import get_categories_with_listings
from listings.models import Listing
from listings.views import get_listing_detail_url


class SitemapView(View):
    def get(self, request):
        statuses = [
            Listing.Status.PUBLISHED,
            Listing.Status.RESERVED,
            Listing.Status.RESERVATION_ACCEPTED,
        ]
        listings = Listing.objects.filter(status__in=statuses).order_by("-updated_at")[
            :1000
        ]
        category_paths = get_categories_with_listings(statuses)
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
            urls.append(
                request.build_absolute_uri(
                    reverse("category_listings", kwargs={"slug": category.slug})
                )
            )
        for city in city_rows:
            urls.append(
                request.build_absolute_uri(
                    reverse("city_listings", kwargs={"slug": slugify(city)})
                )
            )

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
            lines.append(
                f"    <lastmod>{listing.updated_at.date().isoformat()}</lastmod>"
            )
            lines.append("  </url>")
        lines.append("</urlset>")
        return HttpResponse("\n".join(lines), content_type="application/xml")


class HealthCheckView(View):
    def get(self, request):
        status_code = 200
        payload = {"database": "ok", "redis": "ok"}
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
        except OperationalError:
            payload["database"] = "error"
            status_code = 503
        try:
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                socket_connect_timeout=1,
            )
            redis_client.ping()
        except redis.RedisError:
            payload["redis"] = "error"
            status_code = 503
        return JsonResponse(payload, status=status_code)
