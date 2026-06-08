from django.contrib import admin
from .models import Roast


@admin.register(Roast)
class RoastAdmin(admin.ModelAdmin):
    list_display = ("archetype", "slug", "is_published", "created_on")
    prepopulated_fields = {"slug": ("archetype",)}