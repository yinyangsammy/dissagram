from django.shortcuts import render, get_object_or_404
from .models import Roast
from dissers.models import TargetArchetype, RoastStyle


def roast_feed(request):
    """
    Public showcase — all published Roasts.
    """
    roasts = Roast.objects.filter(
        is_published=True
    ).select_related("archetype").order_by("-created_on")

    style_filter = request.GET.get("style")
    archetype_filter = request.GET.get("archetype")

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
    Shows all public disses for that archetype.
    """
    roast = get_object_or_404(Roast, slug=slug, is_published=True)
    public_disses = roast.get_public_disses()

    style_filter = request.GET.get("style")
    if style_filter:
        public_disses = public_disses.filter(
            roast_style__slug=style_filter
        )

    # Needed for the style filter dropdown in the template
    roast_styles = RoastStyle.objects.all().order_by("display_order")

    return render(request, "roasts/roast_detail.html", {
        "roast": roast,
        "public_disses": public_disses,
        "roast_styles": roast_styles,
        "style_filter": style_filter,
    })


def my_roasts(request):
    """
    User's published disses — their public work.
    """
    roasts = []
    if request.user.is_authenticated:
        roasts = request.user.disses.filter(
            is_public=True
        ).select_related(
            "target_archetype", "roast_style"
        ).prefetch_related(
            "selected_lines"
        ).order_by("-created_on")

    return render(request, "roasts/my_roasts.html", {
        "roasts": roasts,
    })


def public_roast_list(request):
    return render(request, "roasts/roast_list.html")
