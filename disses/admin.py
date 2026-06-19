from django import forms
from django.contrib import admin
from .models import Diss, DissLine, PremiumDissLine


# ═══════════════════════════════════════════════════════
# STANDARD DISS LINE
# Category restricted to free categories (e.g. "Diss Line").
# Roast Style is required here, even though the underlying
# model field is nullable — nullable only exists to support
# Premium Diss Lines below.
# ═══════════════════════════════════════════════════════

class StandardDissLineForm(forms.ModelForm):
    class Meta:
        model = DissLine
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["roast_style"].required = True

        from dissers.models import RoastCategory
        self.fields["category"].queryset = RoastCategory.objects.filter(
            is_free=True
        )


@admin.register(DissLine)
class DissLineAdmin(admin.ModelAdmin):
    form = StandardDissLineForm
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

    def get_queryset(self, request):
        # Standard list = free-category lines (or uncategorised legacy lines)
        return super().get_queryset(request).exclude(category__is_free=False)

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = "Content"


# ═══════════════════════════════════════════════════════
# PREMIUM DISS LINE
# Category restricted to premium (non-free) categories —
# LinkedIn Endorsement, Internal Monologue, etc.
# Roast Style field hidden entirely — these lines apply to
# every roast style, so roast_style is force-saved as None.
# ═══════════════════════════════════════════════════════

class PremiumDissLineForm(forms.ModelForm):
    class Meta:
        model = DissLine
        exclude = ("roast_style",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from dissers.models import RoastCategory
        self.fields["category"].queryset = RoastCategory.objects.filter(
            is_free=False
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.roast_style = None
        if commit:
            instance.save()
        return instance


@admin.register(PremiumDissLine)
class PremiumDissLineAdmin(admin.ModelAdmin):
    form = PremiumDissLineForm
    list_display = (
        "archetype",
        "category",
        "content_preview",
        "status",
        "display_order",
    )
    list_filter = (
        "archetype",
        "category",
        "status",
    )
    search_fields = ("content",)
    ordering = ("archetype", "display_order")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(category__is_free=False)

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = "Content"


# ═══════════════════════════════════════════════════════
# DISS
# ═══════════════════════════════════════════════════════

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