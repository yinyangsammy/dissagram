from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from dissers.models import TargetArchetype
from disses.models import Diss


class Roast(models.Model):
    """
    The public pile-on page for a TargetArchetype.
    One Roast per archetype — aggregates all public Disses.
    Mirrors Itinerary in Hip Trip Hooray.
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
        if not self.slug:
            self.slug = slugify(self.archetype.name)
        super().save(*args, **kwargs)

    def get_public_disses(self):
        return Diss.objects.filter(
            target_archetype=self.archetype,
            is_public=True
        ).order_by("-created_on")

    def __str__(self):
        return f"Roast: {self.archetype.name}"