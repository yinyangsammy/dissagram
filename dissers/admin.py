from django.contrib import admin
from .models import RoastCategory, RoastStyle, TargetArchetype, Disser


@admin.register(Disser)
class DisserAdmin(admin.ModelAdmin):
    list_display = ("user", "favourite_style", "burns_deployed", "created_on")


@admin.register(RoastCategory)
class RoastCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "is_free", "required_pack_level", "display_order")
    list_filter = ("is_free",)
    ordering = ("display_order",)


@admin.register(RoastStyle)
class RoastStyleAdmin(admin.ModelAdmin):
    list_display = (
        "name", "emoji", "tagline", "is_free",
        "display_order", "unlock_priority",
    )
    list_editable = ("display_order", "unlock_priority")
    list_filter = ("is_free",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order",)
    fieldsets = (
        (None, {
            "fields": (
                "name", "slug", "tagline", "description",
                "example_line", "emoji", "avatar", "is_free",
            )
        }),
        ("Ordering", {
            "fields": ("display_order", "unlock_priority"),
            "description": (
                "Display Order = visual position in the Step 2 picker "
                "grid only. Unlock Priority = which styles count as "
                "'first' for pack tiering. These are independent — "
                "rearrange one without affecting the other."
            ),
        }),
    )


@admin.register(TargetArchetype)
class TargetArchetypeAdmin(admin.ModelAdmin):
    list_display = (
        "name", "emoji", "difficulty_level", "gender", "is_free",
        "display_order", "unlock_priority",
    )
    list_editable = ("display_order", "unlock_priority")
    list_filter = ("is_free", "difficulty_level", "gender")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order",)
    fieldsets = (
        (None, {
            "fields": (
                "name", "slug", "description", "emoji",
                "traits", "weaknesses", "difficulty_level",
                "catchphrase", "avatar", "gender", "is_free",
            )
        }),
        ("Ordering", {
            "fields": ("display_order", "unlock_priority"),
            "description": (
                "Display Order = visual position in the Step 1 "
                "carousel only. Unlock Priority = which archetypes "
                "count as 'first' for pack tiering. These are "
                "independent — rearrange one without affecting "
                "the other."
            ),
        }),
    )