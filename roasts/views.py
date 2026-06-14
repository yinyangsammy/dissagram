"""
roasts/views.py

Public-facing roast pages.
roast_feed   — all published roast pages with filters
roast_detail — single archetype pile-on page
my_roasts    — logged-in user's published disses
"""

from django.shortcuts import render, get_object_or_404
from .models import Roast
from dissers.models import TargetArchetype, RoastStyle
from disses.models import Diss


def roast_feed(request):
    """
    Public showcase — all published Roasts.
    Filterable by archetype slug and roast style slug.
    Annotates each roast with its public diss count for display.
    """
    roasts = Roast.objects.filter(
        is_published=True
    ).select_related("archetype").order_by("-created_on")

    style_filter = request.GET.get("style", "")
    archetype_filter = request.GET.get("archetype", "")

    # Apply archetype filter
    if archetype_filter:
        roasts = roasts.filter(archetype__slug=archetype_filter)

    # Apply style filter — only show roasts that have at least one
    # public diss in that style
    if style_filter:
        # Get archetype IDs that have public disses in this style
        archetype_ids = Diss.objects.filter(
            roast_style__slug=style_filter,
            is_public=True,
        ).values_list("target_archetype_id", flat=True).distinct()
        roasts = roasts.filter(archetype_id__in=archetype_ids)

    roast_styles = RoastStyle.objects.all().order_by("display_order")
    archetypes = TargetArchetype.objects.all().order_by("display_order")

    return render(request, "roasts/roast_feed.html", {
        "roasts": roasts,
        "roast_styles": roast_styles,
        "archetypes": archetypes,
        "style_filter": style_filter,
        "archetype_filter": archetype_filter,
    })


def roast_detail(request, slug):
    """
    The pile-on page for one archetype.
    Shows all public published disses for that archetype.
    Filterable by roast style.
    Only shows roast styles that have at least one public diss.
    """
    roast = get_object_or_404(Roast, slug=slug, is_published=True)

    style_filter = request.GET.get("style", "")

    # Base queryset — all public published disses for this archetype
    public_disses = Diss.objects.filter(
        target_archetype=roast.archetype,
        is_public=True,
        status="published"
    ).select_related(
        "author", "roast_style"
    ).prefetch_related(
        "selected_lines__category"
    ).order_by("-created_on")

    # Apply style filter if present
    if style_filter:
        public_disses = public_disses.filter(
            roast_style__slug=style_filter
        )

    # Only show styles that actually have public disses for this archetype
    # avoids showing empty filter options
    roast_styles = RoastStyle.objects.filter(
        disses__target_archetype=roast.archetype,
        disses__is_public=True,
        disses__status="published"
    ).distinct().order_by("display_order")

    return render(request, "roasts/roast_detail.html", {
        "roast": roast,
        "public_disses": public_disses,
        "roast_styles": roast_styles,
        "style_filter": style_filter,
    })


def my_roasts(request):
    """
    User's own published disses — their public contribution to the feed.
    Shown as diss cards, not roast pages.
    """
    roasts = []
    if request.user.is_authenticated:
        roasts = request.user.disses.filter(
            is_public=True,
            status="published"
        ).select_related(
            "target_archetype", "roast_style"
        ).prefetch_related(
            "selected_lines"
        ).order_by("-created_on")

    return render(request, "roasts/my_roasts.html", {
        "roasts": roasts,
    })


def public_roast_list(request):
    """Placeholder — redirects to roast_feed."""
    return render(request, "roasts/roast_list.html")
