from django.contrib import admin
from .models import Package, Order


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "archetype_count",
        "roast_style_count",
        "standard_diss_line_count",
        "premium_diss_line_count",
        "max_line_selections",
        "includes_leaderboard",
        "is_active",
        "display_order",
    )
    list_filter = ("is_active", "includes_leaderboard")
    search_fields = ("name", "tagline")
    ordering = ("display_order",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "user",
        "package",
        "status",
        "amount_paid",
        "gifted_to",
        "created_on",
    )
    list_filter = ("status",)
    search_fields = ("user__username", "stripe_payment_id")
    readonly_fields = ("created_on",)