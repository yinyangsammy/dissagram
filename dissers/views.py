from django.shortcuts import render, get_object_or_404
from .models import RoastStyle, TargetArchetype


def disser_list(request):
    """
    Browse all RoastStyles — like browsing categories
    in Hip Trip Hooray.
    """
    roast_styles = RoastStyle.objects.all().order_by("display_order")
    archetypes = TargetArchetype.objects.all().order_by("display_order")
    return render(request, "dissers/disser_list.html", {
        "roast_styles": roast_styles,
        "archetypes": archetypes,
    })


def disser_detail(request, pk):
    """
    Detail page for a single RoastStyle —
    shows example lines and commission button.
    """
    roast_style = get_object_or_404(RoastStyle, pk=pk)
    archetypes = TargetArchetype.objects.all().order_by("display_order")
    return render(request, "dissers/disser_detail.html", {
        "roast_style": roast_style,
        "archetypes": archetypes,
    })
