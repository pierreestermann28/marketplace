from django.urls import path

from .views import CityAutocompleteView

app_name = "location"

urlpatterns = [
    path("cities/autocomplete/", CityAutocompleteView.as_view(), name="city-autocomplete"),
]
