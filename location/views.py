from django.http import JsonResponse
from django.views import View

from .models import City


class CityAutocompleteView(View):
    """Return fast name or postal code matches for the client autocomplete widget."""

    DEFAULT_LIMIT = 25
    MAX_LIMIT = 100

    def get(self, request):
        query = request.GET.get("q", "").strip()
        postal_code = request.GET.get("postal_code", "").strip()
        limit = self._parse_limit(request.GET.get("limit"))

        if not query and not postal_code:
            return JsonResponse({"results": []})

        city_qs = City.objects.all()
        if query:
            city_qs = city_qs.filter(name__istartswith=query)
        if postal_code:
            city_qs = city_qs.filter(postal_code__startswith=postal_code)

        city_qs = city_qs.order_by("name", "postal_code")[:limit]
        payload = [
            {
                "id": city.id,
                "name": city.name,
                "postal_code": city.postal_code,
                "slug": city.slug,
                "display_name": f"{city.name} ({city.postal_code})",
                "department": city.department_name,
                "region": city.region_name,
            }
            for city in city_qs
        ]

        return JsonResponse({"results": payload})

    def _parse_limit(self, value):
        try:
            limit = int(value)
        except (TypeError, ValueError):
            limit = self.DEFAULT_LIMIT

        if limit < 1:
            limit = self.DEFAULT_LIMIT
        return min(limit, self.MAX_LIMIT)
