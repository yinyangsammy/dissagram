import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from dissers.models import RoastStyle, TargetArchetype
from .forms import DissForm
from .models import Diss, DissLine


# ═══════════════════════════════════════════════════════
# HELPERS — Freemium lock logic
# ═══════════════════════════════════════════════════════

def _get_user_unlocked_counts(user):
    """
    Returns the maximum archetype + roast_style counts
    the user has unlocked via completed orders.
    Uses the highest pack purchased (not additive).
    """
    from orders.models import Order

    if not user.is_authenticated:
        return 0, 0

    completed_orders = Order.objects.filter(
        user=user,
        status="complete"
    ).select_related("package")

    max_archetypes = 0
    max_roast_styles = 0

    for order in completed_orders:
        if order.package:
            max_archetypes = max(
                max_archetypes,
                order.package.archetype_count
            )
            max_roast_styles = max(
                max_roast_styles,
                order.package.roast_style_count
            )

    return max_archetypes, max_roast_styles


def _get_user_pack_level(user):
    """
    Returns the highest pack level (display_order) the user owns.
    0 = free tier, 1 = Diss Pack, 2 = Burn Pack.
    Used to gate premium diss categories.
    """
    from orders.models import Order

    if not user.is_authenticated:
        return 0

    completed = Order.objects.filter(
        user=user,
        status="complete"
    ).select_related("package")

    level = 0
    for order in completed:
        if order.package:
            level = max(level, order.package.display_order)

    return level


def _get_accessible_category_names(user):
    """
    Returns a set of RoastCategory names the user can see.
    Free categories always included.
    Premium categories unlocked by pack level.
    """
    from dissers.models import RoastCategory

    pack_level = _get_user_pack_level(user)

    accessible = set(
        RoastCategory.objects.filter(
            required_pack_level__lte=pack_level
        ).values_list("name", flat=True)
    )

    # Safety fallback — always include free categories
    free_cats = set(
        RoastCategory.objects.filter(
            is_free=True
        ).values_list("name", flat=True)
    )

    return accessible | free_cats


def _archetype_json(archetypes, user):
    """
    Builds the JSON payload for the archetype carousel.
    Includes locked state and filtered diss lines per archetype.
    """
    max_archetypes, _ = _get_user_unlocked_counts(user)
    accessible_categories = _get_accessible_category_names(user)

    data = []
    paid_count = 0

    for a in archetypes:
        # Free archetypes always unlocked
        if a.is_free:
            locked = False
        else:
            paid_count += 1
            locked = paid_count > max_archetypes

        # Build disslines filtered by accessible categories
        lines_by_style = {}
        for line in a.diss_lines.filter(
            status="approved"
        ).select_related("roast_style", "category").order_by("display_order"):

            cat_name = line.category.name if line.category else "Diss Line"

            # Skip lines in categories the user hasn't unlocked
            if cat_name not in accessible_categories:
                continue

            sid = line.roast_style_id
            if sid not in lines_by_style:
                lines_by_style[sid] = []

            lines_by_style[sid].append({
                "id": line.id,
                "type": cat_name,
                "content": line.content,
                "roast_style_id": sid,
            })

        # Flatten disslines into a single list
        all_lines = [
            line
            for lines in lines_by_style.values()
            for line in lines
        ]

        data.append({
            "id": a.id,
            "name": a.name,
            "slug": a.slug,
            "emoji": a.emoji or "",
            "avatar_url": a.avatar.url if a.avatar else "",
            "traits": [
                t.strip() for t in (a.traits or "").splitlines()
                if t.strip()
            ][:3],
            "catchphrase": a.catchphrase or "",
            "difficulty": a.difficulty_level or "mid",
            "difficulty_label": a.get_difficulty_level_display(),
            "is_free": a.is_free,
            "locked": locked,
            "diss_lines": all_lines,
        })

    return json.dumps(data)


def _roast_style_json(roast_styles, user):
    """
    Builds the JSON payload for the roast style selector.
    Includes locked state per style.
    """
    _, max_roast_styles = _get_user_unlocked_counts(user)

    data = []
    paid_count = 0

    for s in roast_styles:
        if s.is_free:
            locked = False
        else:
            paid_count += 1
            locked = paid_count > max_roast_styles

        data.append({
            "id": s.id,
            "name": s.name,
            "emoji": s.emoji or "",
            "tagline": s.tagline or "",
            "avatar_url": s.avatar.url if s.avatar else "",
            "is_free": s.is_free,
            "locked": locked,
        })

    return json.dumps(data)


# ═══════════════════════════════════════════════════════
# VIEWS
# ═══════════════════════════════════════════════════════

def diss_example(request):
    """Public example page — no login required."""
    return render(request, "disses/diss_example.html")


def my_disses(request):
    """
    Shows the logged-in user's own disses.
    Anonymous users see an empty list.
    """
    disses = []
    if request.user.is_authenticated:
        disses = (
            Diss.objects
            .filter(author=request.user)
            .select_related("target_archetype", "roast_style")
            .prefetch_related("selected_lines")
            .order_by("-created_on")
        )
    return render(request, "disses/my_disses.html", {"disses": disses})


@login_required
def diss_create(request):
    """
    Main diss builder — step-by-step carousel form.
    Archetype → RoastStyle → DissLines → Save.
    Locked content determined by user's purchased packs.
    """
    archetypes = TargetArchetype.objects.all().order_by("display_order")
    roast_styles = RoastStyle.objects.all().order_by("display_order")

    if request.method == "POST":
        archetype_id = request.POST.get("target_archetype")
        archetype_obj = None
        if archetype_id:
            try:
                archetype_obj = TargetArchetype.objects.get(pk=archetype_id)
            except TargetArchetype.DoesNotExist:
                pass

        form = DissForm(request.POST, archetype=archetype_obj)

        if form.is_valid():
            diss = form.save(commit=False)
            diss.author = request.user
            diss.save()
            form.save_m2m()
            messages.success(
                request,
                f"🔥 Diss locked and loaded against "
                f"{diss.target_archetype}!"
            )
            return redirect("disses:my_disses")
    else:
        form = DissForm()

    context = {
        "form": form,
        "archetypes_json": _archetype_json(archetypes, request.user),
        "roast_styles_json": _roast_style_json(roast_styles, request.user),
        "archetypes": archetypes,
        "roast_styles": roast_styles,
        "max_line_selections": _get_max_line_selections(request.user),
    }
    return render(request, "disses/diss_form.html", context)


@login_required
def diss_edit(request, pk):
    """
    Edit an existing diss — restores carousel state from saved values.
    Only the author can edit their own diss.
    """
    diss = get_object_or_404(Diss, pk=pk, author=request.user)

    archetypes = TargetArchetype.objects.all().order_by("display_order")
    roast_styles = RoastStyle.objects.all().order_by("display_order")

    if request.method == "POST":
        archetype_id = request.POST.get("target_archetype")
        archetype_obj = None
        if archetype_id:
            try:
                archetype_obj = TargetArchetype.objects.get(pk=archetype_id)
            except TargetArchetype.DoesNotExist:
                pass

        form = DissForm(request.POST, instance=diss, archetype=archetype_obj)

        if form.is_valid():
            form.save()
            messages.success(request, "✏️ Diss updated.")
            return redirect("disses:my_disses")
    else:
        form = DissForm(instance=diss, archetype=diss.target_archetype)

    context = {
        "form": form,
        "diss": diss,
        "editing": True,
        "archetypes_json": _archetype_json(archetypes, request.user),
        "roast_styles_json": _roast_style_json(roast_styles, request.user),
        "archetypes": archetypes,
        "roast_styles": roast_styles,
        # Pre-selected IDs — used by JS to restore carousel on edit
        "selected_archetype_id": diss.target_archetype_id or "",
        "selected_roast_style_id": diss.roast_style_id or "",
        "selected_line_ids": list(
            diss.selected_lines.values_list("id", flat=True)
        ),
        "max_line_selections": _get_max_line_selections(request.user),
    }
    return render(request, "disses/diss_form.html", context)


def diss_detail(request, pk):
    """
    Public diss detail page.
    Non-public disses only visible to their author.
    """
    diss = get_object_or_404(Diss, pk=pk)
    if not diss.is_public and diss.author != request.user:
        from django.http import Http404
        raise Http404
    return render(request, "disses/diss_detail.html", {"diss": diss})


@login_required
def diss_delete(request, pk):
    """
    Delete a diss — POST only, with confirmation template.
    Only the author can delete their own diss.
    """
    diss = get_object_or_404(Diss, pk=pk, author=request.user)
    if request.method == "POST":
        diss.delete()
        messages.success(request, "💀 Diss deleted.")
        return redirect("disses:my_disses")
    return render(request, "disses/diss_confirm_delete.html", {"diss": diss})


def _get_max_line_selections(user):
    """Returns max disslines user can select based on pack owned."""
    from orders.models import Order

    if not user.is_authenticated:
        return 1

    completed = Order.objects.filter(
        user=user,
        status="complete"
    ).select_related("package")

    max_lines = 1  # free tier default
    for order in completed:
        if order.package and order.package.max_line_selections:
            max_lines = max(max_lines, order.package.max_line_selections)

    return max_lines


@login_required
def deploy_burn(request, pk):
    """
    Deploy a diss as a public Burn.
    Creates or retrieves the Roast for the archetype,
    publishes the diss, redirects to the public roast page.
    Mirrors publish/unpublish pattern from HipTripHooray.
    """
    from roasts.models import Roast
    from django.utils.text import slugify

    # DEBUG — remove after fix
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"deploy_burn called — method: {request.method}, pk: {pk}, POST: {request.POST}")
    
    diss = get_object_or_404(Diss, pk=pk, author=request.user)

    if request.method == "POST":
        action = request.POST.get("action", "deploy")

        if action == "undeploy":
            diss.is_public = False
            diss.status = "draft"
            diss.save()
            messages.success(
                request, "🔒 Burn recalled — diss set back to draft."
            )
            return redirect("disses:diss_detail", pk=diss.pk)

        # Validate before doing anything
        if not diss.selected_lines.exists():
            messages.error(
                request,
                "⚠️ Add at least one burn line before deploying."
            )
            return redirect("disses:diss_detail", pk=diss.pk)

        if not diss.target_archetype:
            messages.error(request, "⚠️ No target archetype selected.")
            return redirect("disses:diss_detail", pk=diss.pk)

        # ── Step 1: Publish the diss FIRST ──────────────────
        diss.is_public = True
        diss.status = "published"
        diss.save()

        # ── Step 2: Ensure Roast exists — separately ────────
        # Explicit slug prevents save() failure on get_or_create
        archetype_slug = slugify(diss.target_archetype.name)

        try:
            roast = Roast.objects.get(archetype=diss.target_archetype)
        except Roast.DoesNotExist:
            roast = Roast.objects.create(
                archetype=diss.target_archetype,
                slug=archetype_slug,
                intro=(
                    f"The community weighs in on "
                    f"{diss.target_archetype.name}."
                ),
                is_published=True,
            )

        # Safety — ensure slug is set even on existing roasts
        if not roast.slug:
            roast.slug = archetype_slug
            roast.save()

        messages.success(
            request,
            f"🔥 Burn deployed! "
            f"{diss.target_archetype.name} has been roasted publicly."
        )
        return redirect("roasts:roast_detail", slug=roast.slug)

    # GET — confirmation page
    return render(
        request,
        "disses/deploy_burn_confirm.html",
        {"diss": diss}
    )