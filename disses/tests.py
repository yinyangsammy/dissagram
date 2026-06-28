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

    def test_dissline_status_is_approved(self):
        """DissLine status can be set to approved."""
        self.assertEqual(self.diss_line.status, "approved")

    def test_dissline_ordering(self):
        """DissLines order by archetype, roast_style and display_order."""
        second_line = DissLine.objects.create(
            archetype=self.archetype,
            roast_style=self.roast_style,
            category=self.category,
            content="Second burn line.",
            status="approved",
            display_order=2,
        )

        lines = list(DissLine.objects.filter(archetype=self.archetype))

        self.assertEqual(lines[0].display_order, 1)
        self.assertEqual(lines[1].display_order, 2)
        self.assertEqual(lines[1], second_line)

    def test_only_approved_lines_queryset(self):
        """Filtering for approved lines excludes pending/rejected."""
        DissLine.objects.create(
            archetype=self.archetype,
            roast_style=self.roast_style,
            category=self.category,
            content="Pending burn.",
            status="pending",
            display_order=3,
        )

        approved = DissLine.objects.filter(
            archetype=self.archetype,
            status="approved",
        )

        self.assertEqual(approved.count(), 1)
        self.assertEqual(
            approved.first().content,
            "Your sermons take me back to a constipated hippopotamus.",
        )

    def test_dissline_free_flag_can_be_true(self):
        """DissLine can be marked as free for MVP trial content."""
        self.diss_line.is_free = True
        self.diss_line.save()

        self.diss_line.refresh_from_db()

        self.assertTrue(self.diss_line.is_free)

    def test_free_lines_can_be_filtered_by_archetype_and_roast_style(self):
        """Free trial lines can be filtered by selected archetype and roast style."""
        self.diss_line.is_free = True
        self.diss_line.save()

        free_lines = DissLine.objects.filter(
            archetype=self.archetype,
            roast_style=self.roast_style,
            is_free=True,
            status="approved",
        )

        self.assertEqual(free_lines.count(), 1)
        self.assertEqual(free_lines.first(), self.diss_line)


class DissModelTest(TestCase):
    """
    Tests for the Diss model.

    A Diss is a user's assembled selection of DissLines
    for a specific Archetype + RoastStyle combination.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="yinyangsammy",
            password="testpass123",
        )

        self.archetype = TargetArchetype.objects.create(
            name="Gym Narcissist",
            slug="gym-narcissist",
        )

        self.roast_style = RoastStyle.objects.create(
            name="Battle Rapper",
            slug="battle-rapper",
        )

        self.category = RoastCategory.objects.create(
            name="Diss Line",
            emoji="🔥",
            display_order=1,
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

    def test_diss_can_store_selected_lines(self):
        """A Diss can store the user's selected DissLines."""
        diss_line = DissLine.objects.create(
            archetype=self.archetype,
            roast_style=self.roast_style,
            category=self.category,
            content="Your biceps have a press office.",
            status="approved",
            display_order=1,
        )

        self.diss.selected_lines.add(diss_line)

        self.assertEqual(self.diss.selected_lines.count(), 1)
        self.assertIn(diss_line, self.diss.selected_lines.all())

    def test_diss_can_be_published_and_made_public(self):
        """A Diss can be moved from draft/private to published/public."""
        self.diss.status = "published"
        self.diss.is_public = True
        self.diss.save()

        self.diss.refresh_from_db()

        self.assertEqual(self.diss.status, "published")
        self.assertTrue(self.diss.is_public)