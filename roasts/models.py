"""
roasts/models.py

The Roast model represents a public pile-on page for a TargetArchetype.
One Roast per archetype — aggregates all public Disses targeting it.
Mirrors Itinerary in Hip Trip Hooray.

Future: DissRating model (1-5 flames per diss, powers leaderboard)
will link here via FK on Diss.
"""

from django.db import models
from django.utils.text import slugify
from dissers.models import TargetArchetype
from disses.models import Diss


class Roast(models.Model):
    """
    Public pile-on page for one TargetArchetype.
    Created automatically on first Deploy Burn for that archetype.
    """
    archetype = models.OneToOneField(
        TargetArchetype,
        on_delete=models.CASCADE,
        related_name="roast"
    )
    slug = models.SlugField(unique=True, blank=True)
    intro = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_on"]
        verbose_name = "Roast"
        verbose_name_plural = "Roasts"

    def save(self, *args, **kwargs):
        # Auto-generate slug from archetype name on first save
        if not self.slug:
            base_slug = slugify(self.archetype.name)
            self.slug = base_slug
        super().save(*args, **kwargs)

    def get_public_disses(self):
        """
        Returns all published public disses for this archetype.
        Used in templates and roast_feed view for pile-on counts.
        """
        return Diss.objects.filter(
            target_archetype=self.archetype,
            is_public=True,
            status="published"
        ).select_related(
            "author", "roast_style"
        ).prefetch_related(
            "selected_lines"
        ).order_by("-created_on")

    def get_public_disses_count(self):
        """Convenience method for template count without extra query."""
        return Diss.objects.filter(
            target_archetype=self.archetype,
            is_public=True,
            status="published"
        ).count()

    def __str__(self):
        return f"Roast: {self.archetype.name}"
