import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from dissers.models import RoastStyle, TargetArchetype
from .forms import DissForm
from .models import Diss, DissLine


# ─────────────────────────────────────────────
# Helper — build the JSON payload the carousel JS needs
# ─────────────────────────────────────────────

def _archetype_json(archetypes, diss_lines_qs, roast_styles):
    """
    Serialise archetypes → JSON for the carousel.
    Each archetype carries:
      - basic fields (id, name, emoji, difficulty_level, traits, weaknesses)
      - roast_style_ids  : IDs of styles that have at least one line for it
      - diss_lines       : approved lines grouped for JS filtering
    """

    # Map archetype_id → list of style IDs that actually have lines for it
    style_ids_by_archetype = {}
    lines_by_archetype = {}

    for line in diss_lines_qs.select_related("archetype", "roast_style"):
        aid = line.archetype_id
        sid = line.roast_style_id

        style_ids_by_archetype.setdefault(aid, set())
        if sid:
            style_ids_by_archetype[aid].add(sid)

        lines_by_archetype.setdefault(aid, [])
        lines_by_archetype[aid].append({
            "id": line.id,
            "type": line.category.name if line.category else "Diss Line",  # ← fixed
            "content": line.content,
            "roast_style_id": sid,
        })

    data = []
    for arch in archetypes:
        traits = [t.strip() for t in arch.traits.splitlines() if t.strip()]
        weaknesses = [w.strip() for w in arch.weaknesses.splitlines() if w.strip()]

        # Difficulty → integer for star rendering
        diff_map = {"easy": 1, "mid": 2, "hard": 3, "legendary": 5}
        diff_int = diff_map.get(arch.difficulty_level, 2)

        # Avatar URL — empty string if no image uploaded yet
        avatar_url = arch.avatar.url if arch.avatar else ""

        data.append({
            "id": arch.id,
            "name": arch.name,
            "emoji": arch.emoji,
            "difficulty": diff_int,
            "difficulty_label": arch.get_difficulty_level_display(),
            "traits": traits[:3],          # top 3 for the card preview
            "weaknesses": weaknesses[:3],
            "avatar_url": avatar_url,
            "roast_style_ids": list(style_ids_by_archetype.get(arch.id, [])),
            "diss_lines": lines_by_archetype.get(arch.id, []),
        })

    return json.dumps(data)


def _roast_style_json(roast_styles):
    return json.dumps([
        {
            "id": s.id,
            "name": s.name,
            "emoji": s.emoji,
            "tagline": s.tagline,
            "avatar_url": s.avatar.url if s.avatar else "",
        }
        for s in roast_styles
    ])


# ─────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────

def diss_example(request):
    return render(request, "disses/diss_example.html")


def my_disses(request):
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
    archetypes = TargetArchetype.objects.all().order_by("display_order")
    roast_styles = RoastStyle.objects.all().order_by("display_order")
    diss_lines_qs = DissLine.objects.filter(status="approved").select_related(
        "archetype", "roast_style"
    )

    if request.method == "POST":
        # Resolve archetype instance for scoped queryset
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
            form.save_m2m()  # save selected_lines M2M
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
        "archetypes_json": _archetype_json(archetypes, diss_lines_qs, roast_styles),
        "roast_styles_json": _roast_style_json(roast_styles),
        # Pass raw querysets too (for non-JS fallback if ever needed)
        "archetypes": archetypes,
        "roast_styles": roast_styles,
    }
    return render(request, "disses/diss_form.html", context)


@login_required
def diss_edit(request, pk):
    diss = get_object_or_404(Diss, pk=pk, author=request.user)

    archetypes = TargetArchetype.objects.all().order_by("display_order")
    roast_styles = RoastStyle.objects.all().order_by("display_order")
    diss_lines_qs = DissLine.objects.filter(status="approved").select_related(
        "archetype", "roast_style"
    )

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
        "archetypes_json": _archetype_json(archetypes, diss_lines_qs, roast_styles),
        "roast_styles_json": _roast_style_json(roast_styles),
        "archetypes": archetypes,
        "roast_styles": roast_styles,
        # Pre-selected IDs for JS to restore the carousel state on edit
        "selected_archetype_id": diss.target_archetype_id or "",
        "selected_roast_style_id": diss.roast_style_id or "",
        "selected_line_ids": list(
            diss.selected_lines.values_list("id", flat=True)
        ),
    }
    return render(request, "disses/diss_form.html", context)


def diss_detail(request, pk):
    diss = get_object_or_404(Diss, pk=pk)
    # Non-public disses only visible to their author
    if not diss.is_public and diss.author != request.user:
        from django.http import Http404
        raise Http404
    return render(request, "disses/diss_detail.html", {"diss": diss})


@login_required
def diss_delete(request, pk):
    diss = get_object_or_404(Diss, pk=pk, author=request.user)
    if request.method == "POST":
        diss.delete()
        messages.success(request, "💀 Diss deleted.")
        return redirect("disses:my_disses")
    return render(request, "disses/diss_confirm_delete.html", {"diss": diss})
