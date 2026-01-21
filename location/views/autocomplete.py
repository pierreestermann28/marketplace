from django.http import JsonResponse
from django.views import View

from location.queries import autocomplete_cities


class CityAutocompleteView(View):
    """Return fast name or postal code matches for the client autocomplete widget."""

    def get(self, request):
        query = request.GET.get("q", "").strip()
        postal_code = request.GET.get("postal_code", "").strip()
        if not query and not postal_code:
            return JsonResponse({"results": []})

        payload = autocomplete_cities(
            query=query,
            postal_code=postal_code,
            limit=request.GET.get("limit"),
        )
        return JsonResponse({"results": payload})
