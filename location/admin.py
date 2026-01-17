from django.contrib import admin

from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "postal_code", "department_name", "region_name")
    search_fields = ("name", "postal_code")
    list_filter = ("department_name", "region_name")
