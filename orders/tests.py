from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from dissers.models import RoastStyle, TargetArchetype
from orders.models import Order, Package
from orders.views import _send_order_confirmation


class OrdersAppTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="rambowordsmith",
            email="rambo@example.com",
            password="testpass123",
        )

        TargetArchetype.objects.create(
            name="Gym Narcissist",
            slug="gym-narcissist",
            description="Free starter archetype",
            emoji="💪",
            is_free=True,
            unlock_priority=1,
            display_order=1,
        )

        TargetArchetype.objects.create(
            name="Fake Guru",
            slug="fake-guru",
            description="Paid archetype",
            emoji="🧘",
            is_free=False,
            unlock_priority=1,
            display_order=2,
        )

        RoastStyle.objects.create(
            name="Shakespearean Savage",
            slug="shakespearean-savage",
            tagline="Poetic disrespect",
            description="Free starter style",
            example_line="Thou art a walking group project.",
            emoji="🎭",
            is_free=True,
            unlock_priority=1,
            display_order=1,
        )

        RoastStyle.objects.create(
            name="Haughty Headmistress",
            slug="haughty-headmistress",
            tagline="Correcting your existence",
            description="Paid roast style",
            example_line="See me after several years of personal growth.",
            emoji="👑",
            is_free=False,
            unlock_priority=1,
            display_order=2,
        )

        self.package = Package.objects.create(
            name="DISS PACK",
            tagline="Starter pack",
            price="3.99",
            description="Starter package",
            archetype_count=1,
            roast_style_count=1,
            standard_diss_line_count=2,
            premium_diss_line_count=1,
            max_line_selections=3,
            display_order=1,
            is_active=True,
        )

    def test_packages_page_requires_login(self):
        response = self.client.get(reverse("orders:packages"))

        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_view_packages_page(self):
        self.client.login(
            username="rambowordsmith",
            password="testpass123",
        )

        response = self.client.get(reverse("orders:packages"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/packages.html")
        self.assertContains(response, "DISS PACK")

    def test_package_display_includes_free_content(self):
        self.client.login(
            username="rambowordsmith",
            password="testpass123",
        )

        response = self.client.get(reverse("orders:packages"))
        package = list(response.context["packages"])[0]

        self.assertEqual(package.display_archetype_count, 2)
        self.assertEqual(package.display_roast_style_count, 2)

    def test_package_page_shows_standard_and_premium_lines(self):
        self.client.login(
            username="rambowordsmith",
            password="testpass123",
        )

        response = self.client.get(reverse("orders:packages"))

        self.assertContains(response, "Diss Line")
        self.assertContains(response, "Premium Diss Line")

    def test_completed_order_marks_package_as_owned(self):
        Order.objects.create(
            user=self.user,
            package=self.package,
            amount_paid=self.package.price,
            status="complete",
            stripe_payment_id="test_payment_123",
        )

        self.client.login(
            username="rambowordsmith",
            password="testpass123",
        )

        response = self.client.get(reverse("orders:packages"))
        package = list(response.context["packages"])[0]

        self.assertTrue(package.already_owned)
        self.assertEqual(package.purchase_count, 1)
        self.assertContains(response, "PURCHASED")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@dissagram.com",
    )
    def test_order_confirmation_email_is_sent_after_purchase(self):
        order = Order.objects.create(
            user=self.user,
            package=self.package,
            amount_paid=self.package.price,
            status="complete",
            stripe_payment_id="test_payment_123",
        )

        email_sent = _send_order_confirmation(order)

        self.assertTrue(email_sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["rambo@example.com"])
        self.assertIn("DISS PACK", mail.outbox[0].subject)
        self.assertIn("locked and loaded", mail.outbox[0].body)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@dissagram.com",
    )
    def test_order_confirmation_email_is_not_sent_without_user_email(self):
        self.user.email = ""
        self.user.save()

        order = Order.objects.create(
            user=self.user,
            package=self.package,
            amount_paid=self.package.price,
            status="complete",
            stripe_payment_id="test_payment_456",
        )

        email_sent = _send_order_confirmation(order)

        self.assertFalse(email_sent)
        self.assertEqual(len(mail.outbox), 0)