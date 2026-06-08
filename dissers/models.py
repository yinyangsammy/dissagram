from django.db import models
from django.contrib.auth.models import User


class RoastCategory(models.Model):
    """
    Type of roast content.
    e.g. Internal Monologue, CV Highlights, Psyche Report
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    emoji = models.CharField(max_length=10, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]
        verbose_name = "Roast Category"
        verbose_name_plural = "Roast Categories"

    def __str__(self):
        return self.name


class RoastStyle(models.Model):
    """
    The voice/persona of the diss.
    e.g. Shakespearean Savage, Battle Rapper, Corporate HR
    Mirrors Category in Hip Trip Hooray.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    example_line = models.TextField(blank=True)
    emoji = models.CharField(max_length=10, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    is_free = models.BooleanField(
        default=False,
        help_text="Available to free-tier users."
    )
    avatar = models.ImageField(
        upload_to="roast_styles/",
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["display_order"]
        verbose_name = "Roast Style"
        verbose_name_plural = "Roast Styles"

    def __str__(self):
        return self.name


class TargetArchetype(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    emoji = models.CharField(max_length=10, blank=True)
    traits = models.TextField(
        blank=True,
        help_text="One trait per line"
    )
    weaknesses = models.TextField(
        blank=True,
        help_text="One weakness per line"
    )
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ("easy", "Easy"),
            ("mid", "Mid"),
            ("hard", "Hard"),
            ("legendary", "Legendary"),
        ],
        default="mid"
    )
    catchphrase = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. 'Per my last email...'"
    )
    avatar = models.ImageField(
        upload_to="archetypes/",
        blank=True,
        null=True
    )

    display_order = models.PositiveIntegerField(default=0)

    is_free = models.BooleanField(
        default=False,
        help_text="Available to free-tier users."
    )
   
    class Meta:
        ordering = ["display_order"]
        verbose_name = "Target Archetype"
        verbose_name_plural = "Target Archetypes"

    def __str__(self):
        return self.name


class Disser(models.Model):
    """
    Extended arena profile for a registered user.
    One per User — their identity, stats and preferred style.
    Original custom model — no direct Hip Trip Hooray equivalent.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="disser_profile"
    )
    bio = models.TextField(blank=True)
    avatar = models.ImageField(
        upload_to="disser_avatars/",
        blank=True,
        null=True
    )
    favourite_style = models.ForeignKey(
        RoastStyle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fans"
    )
    burns_deployed = models.PositiveIntegerField(default=0)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Disser"
        verbose_name_plural = "Dissers"

    def disses_today(self):
        """Free tier — max 2 disses per day."""
        from django.utils import timezone
        today = timezone.now().date()
        return self.user.disses.filter(
            created_on__date=today
        ).count()

    def can_create_diss(self):
        return self.disses_today() < 2

    def __str__(self):
        return f"{self.user.username}'s Arena Profile"