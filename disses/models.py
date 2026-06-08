from django.db import models
from django.contrib.auth.models import User
from dissers.models import RoastCategory, RoastStyle, TargetArchetype


class Diss(models.Model):
    """
    A user's assembled diss — their chosen lines
    for a specific archetype and style.
    Mirrors Trip in Hip Trip Hooray.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="disses"
    )
    target_archetype = models.ForeignKey(
        "dissers.TargetArchetype",
        on_delete=models.SET_NULL,
        null=True,
        related_name="disses"
    )
    roast_style = models.ForeignKey(
        "dissers.RoastStyle",
        on_delete=models.SET_NULL,
        null=True,
        related_name="disses"
    )
    selected_lines = models.ManyToManyField(
        "DissLine",
        blank=True,
        related_name="used_in_disses",
        help_text="The lines the user picked"
    )
    custom_note = models.TextField(
        blank=True,
        help_text="Optional personal context"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )
    is_public = models.BooleanField(default=False)

    # Riposte chain — future proof, zero cost now
    parent_diss = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ripostes"
    )
    is_riposte = models.BooleanField(default=False)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_on"]
        verbose_name = "Diss"
        verbose_name_plural = "Disses"

    def __str__(self):
        return (
            f"{self.author.username} → "
            f"{self.target_archetype} "
            f"({self.roast_style})"
        )


class DissLine(models.Model):
    category = models.ForeignKey(
        "dissers.RoastCategory",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="diss_lines"
    )
    archetype = models.ForeignKey(          # Single FK — dropdown
        "dissers.TargetArchetype",
        on_delete=models.CASCADE,
        related_name="diss_lines"
    )
    roast_style = models.ForeignKey(        # Single FK — dropdown
        "dissers.RoastStyle",
        on_delete=models.CASCADE,
        related_name="diss_lines"
    )
    content = models.TextField(
        help_text="The actual burn line"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("approved", "Approved"),
            ("pending", "Pending Approval"),
            ("rejected", "Rejected"),
        ],
        default="approved"
    )
    suggested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="suggested_lines"
    )
    is_free = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["archetype", "roast_style", "display_order"]
        verbose_name = "Diss Line"
        verbose_name_plural = "Diss Lines"

    def __str__(self):
        return (
            f"{self.archetype} × {self.roast_style} "
            f"[{self.category}] — {self.content[:50]}"
        )
