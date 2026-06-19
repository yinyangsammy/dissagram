from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from allauth.account.models import EmailAddress

from dissers.models import Disser


class ProfileViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="rambowordsmith",
            email="old@example.com",
            password="testpass123",
        )

    def test_profile_page_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_logged_in_user_can_view_profile(self):
        self.client.login(username="rambowordsmith", password="testpass123")

        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")
        self.assertContains(response, "rambowordsmith")

    def test_profile_creates_disser_if_missing(self):
        self.assertFalse(Disser.objects.filter(user=self.user).exists())

        self.client.login(username="rambowordsmith", password="testpass123")
        self.client.get(reverse("accounts:profile"))

        self.assertTrue(Disser.objects.filter(user=self.user).exists())

    def test_logged_in_user_can_view_profile_edit_page(self):
        self.client.login(username="rambowordsmith", password="testpass123")

        response = self.client.get(reverse("accounts:profile_edit"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile_edit.html")
        self.assertContains(response, "Edit Profile")

    def test_profile_edit_updates_user_email(self):
        self.client.login(username="rambowordsmith", password="testpass123")

        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "email": "new@example.com",
            },
            follow=True,
        )

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.email, "new@example.com")
        self.assertContains(response, "Profile updated")

    def test_profile_edit_syncs_allauth_email_address(self):
        self.client.login(username="rambowordsmith", password="testpass123")

        self.client.post(
            reverse("accounts:profile_edit"),
            {
                "email": "new@example.com",
            },
        )

        email_record = EmailAddress.objects.get(
            user=self.user,
            email="new@example.com",
        )

        self.assertTrue(email_record.primary)
        self.assertTrue(email_record.verified)