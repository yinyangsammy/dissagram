from django.contrib import admin
from .models import RoastCategory, RoastStyle, TargetArchetype, Disser

@admin.register(Disser)
class DisserAdmin(admin.ModelAdmin):
    list_display = ("user", "favourite_style", "burns_deployed", "created_on")


@admin.register(RoastCategory)
class RoastCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "display_order")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order",)


@admin.register(RoastStyle)
class RoastStyleAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "tagline", "is_free", "display_order")
    list_filter = ("is_free",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order",)


@admin.register(TargetArchetype)
class TargetArchetypeAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "difficulty_level", "is_free", "display_order")
    list_filter = ("is_free", "difficulty_level")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order",)
