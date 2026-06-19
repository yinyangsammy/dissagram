from django.contrib import admin
from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "name",
        "email",
        "reason",
        "is_resolved",
        "created_on",
    )
    list_filter = ("reason", "is_resolved", "created_on")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("created_on",)
    ordering = ("-created_on",)