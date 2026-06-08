from django.contrib import admin
from .models import Diss, DissLine


@admin.register(DissLine)
class DissLineAdmin(admin.ModelAdmin):
    list_display = (
        "archetype",
        "roast_style", 
        "category",
        "content_preview",
        "status",
        "is_free",
        "display_order",
    )
    list_filter = (
        "archetype",
        "roast_style",
        "category",
        "status",
        "is_free",
    )
    search_fields = ("content",)
    ordering = ("archetype", "roast_style", "display_order")

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = "Content"


@admin.register(Diss)
class DissAdmin(admin.ModelAdmin):
    list_display = (
        "author",
        "target_archetype",
        "roast_style",
        "status",
        "is_public",
        "is_riposte",
        "created_on",
    )
    list_filter = ("status", "is_public", "roast_style", "is_riposte")
    search_fields = ("author__username",)
    filter_horizontal = ("selected_lines",)
    readonly_fields = ("created_on", "updated_on")