"""
Tests for the Disses app models.

Covers the core DissLine compound relationship
(TargetArchetype × RoastStyle) which is the
central data mechanic of Dissagram.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from dissers.models import TargetArchetype, RoastStyle, RoastCategory
from disses.models import DissLine, Diss


class DissLineModelTest(TestCase):
    """
    Tests for the DissLine model.
    Each DissLine belongs to one TargetArchetype
    and one RoastStyle — the core compound FK relationship.
    """

    def setUp(self):
        self.archetype = TargetArchetype.objects.create(
            name="Fake Guru",
            slug="fake-guru",
            catchphrase="Energy is real, so is my Lambo.",
        )
        self.roast_style = RoastStyle.objects.create(
            name="Haughty Headmistress",
            slug="haughty-headmistress",
        )
        self.category = RoastCategory.objects.create(
            name="Diss Line",
            emoji="🔥",
            display_order=1,
        )
        self.diss_line = DissLine.objects.create(
            archetype=self.archetype,
            roast_style=self.roast_style,
            category=self.category,
            content="Your sermons take me back to a constipated hippopotamus.",
            status="approved",
            display_order=1,
        )

    def test_dissline_str(self):
        """__str__ includes archetype, roast style and content preview."""
        result = str(self.diss_line)
        self.assertIn("Fake Guru", result)
        self.assertIn("Haughty Headmistress", result)

    def test_dissline_belongs_to_correct_archetype(self):
        """DissLine FK resolves to the correct TargetArchetype."""
        self.assertEqual(self.diss_line.archetype.name, "Fake Guru")

    def test_dissline_belongs_to_correct_roast_style(self):
        """DissLine FK resolves to the correct RoastStyle."""
        self.assertEqual(self.diss_line.roast_style.name, "Haughty Headmistress")

    def test_dissline_category(self):
        """DissLine category FK resolves correctly."""
        self.assertEqual(self.diss_line.category.name, "Diss Line")

    def test_dissline_default_status_is_approved(self):
        """DissLines created via admin default to approved."""
        self.assertEqual(self.diss_line.status, "approved")

    def test_dissline_ordering(self):
        """DissLines order by archetype, roast_style, display_order."""
        second_line = DissLine.objects.create(
            archetype=self.archetype,
            roast_style=self.roast_style,
            category=self.category,
            content="Second burn line.",
            display_order=2,
        )
        lines = list(DissLine.objects.filter(archetype=self.archetype))
        self.assertEqual(lines[0].display_order, 1)
        self.assertEqual(lines[1].display_order, 2)

    def test_only_approved_lines_queryset(self):
        """Filtering for approved lines excludes pending/rejected."""
        DissLine.objects.create(
            archetype=self.archetype,
            roast_style=self.roast_style,
            content="Pending burn.",
            status="pending",
            display_order=3,
        )
        approved = DissLine.objects.filter(
            archetype=self.archetype,
            status="approved"
        )
        self.assertEqual(approved.count(), 1)
        self.assertEqual(approved.first().content,
                         "Your sermons take me back to a constipated hippopotamus.")


class DissModelTest(TestCase):
    """
    Tests for the Diss model.
    A Diss is a user's assembled selection of DissLines
    for a specific Archetype + RoastStyle combination.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="yinyangsammy",
            password="testpass123"
        )
        self.archetype = TargetArchetype.objects.create(
            name="Gym Narcissist",
            slug="gym-narcissist",
        )
        self.roast_style = RoastStyle.objects.create(
            name="Battle Rapper",
            slug="battle-rapper",
        )
        self.diss = Diss.objects.create(
            author=self.user,
            target_archetype=self.archetype,
            roast_style=self.roast_style,
            status="draft",
        )

    def test_diss_str(self):
        """__str__ includes author, archetype and roast style."""
        result = str(self.diss)
        self.assertIn("yinyangsammy", result)
        self.assertIn("Gym Narcissist", result)

    def test_diss_defaults_to_draft(self):
        """Newly created Diss defaults to draft status."""
        self.assertEqual(self.diss.status, "draft")

    def test_diss_defaults_to_private(self):
        """Newly created Diss defaults to private (is_public=False)."""
        self.assertFalse(self.diss.is_public)

    def test_diss_author_relationship(self):
        """Diss resolves to the correct author."""
        self.assertEqual(self.diss.author.username, "yinyangsammy")

    def test_diss_selected_lines_empty_by_default(self):
        """A new Diss has no selected lines until user picks them."""
        self.assertEqual(self.diss.selected_lines.count(), 0)
