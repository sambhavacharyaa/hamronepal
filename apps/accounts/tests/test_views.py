import re

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User

from .factories import UserFactory

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
LOCMEM_MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}


def _extract_url(body):
    match = re.search(r"https?://\S+", body)
    assert match, body
    return match.group(0)


@override_settings(CACHES=LOCMEM_CACHE, MAILERS=LOCMEM_MAILERS)
class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_get_register_page(self):
        response = self.client.get("/en/accounts/register/")
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_logs_in_and_sends_verification_email(self):
        response = self.client.post(
            "/en/accounts/register/",
            {
                "email": "newuser@example.com",
                "phone_number": "9800000000",
                "password1": "S0meStrongPass!",
                "password2": "S0meStrongPass!",
            },
        )

        self.assertRedirects(response, reverse("core:dashboard"))
        user = User.objects.get(email="newuser@example.com")
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)

    def test_verification_link_marks_user_verified_and_is_idempotent(self):
        self.client.post(
            "/en/accounts/register/",
            {"email": "verify@example.com", "password1": "S0meStrongPass!", "password2": "S0meStrongPass!"},
        )
        user = User.objects.get(email="verify@example.com")
        verify_path = _extract_url(mail.outbox[0].body).split("testserver", 1)[1]
        self.client.logout()

        self.client.get(verify_path)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

        # Visiting again should not error, and stays verified.
        self.client.get(verify_path)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_registration_rate_limited(self):
        for i in range(11):
            response = self.client.post(
                "/en/accounts/register/",
                {"email": f"rl{i}@example.com", "password1": "S0meStrongPass!", "password2": "S0meStrongPass!"},
            )
        self.assertEqual(response.status_code, 403)


@override_settings(CACHES=LOCMEM_CACHE)
class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = UserFactory(email="login@example.com", password="Str0ngPass!1")

    def test_wrong_password_rejected(self):
        response = self.client.post(
            "/en/accounts/login/", {"username": "login@example.com", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_correct_login_redirects_to_dashboard(self):
        response = self.client.post(
            "/en/accounts/login/", {"username": "login@example.com", "password": "Str0ngPass!1"}
        )
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_login_rate_limited(self):
        for i in range(11):
            response = self.client.post(
                "/en/accounts/login/", {"username": "login@example.com", "password": "wrong"}
            )
        self.assertEqual(response.status_code, 403)


@override_settings(CACHES=LOCMEM_CACHE, MAILERS=LOCMEM_MAILERS)
class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = UserFactory(email="reset@example.com", password="OldPass!123")

    def test_password_reset_flow(self):
        response = self.client.post("/en/accounts/password-reset/", {"email": "reset@example.com"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        reset_path = _extract_url(mail.outbox[0].body).split("testserver", 1)[1]
        response = self.client.get(reset_path, follow=True)
        self.assertEqual(response.status_code, 200)
        final_path = response.redirect_chain[-1][0] if response.redirect_chain else reset_path

        response = self.client.post(
            final_path, {"new_password1": "Br@ndNewPass1", "new_password2": "Br@ndNewPass1"}, follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.client.logout()
        response = self.client.post(
            "/en/accounts/login/", {"username": "reset@example.com", "password": "OldPass!123"}
        )
        self.assertTrue(response.context["form"].errors)

        response = self.client.post(
            "/en/accounts/login/", {"username": "reset@example.com", "password": "Br@ndNewPass1"}
        )
        self.assertEqual(response.status_code, 302)

    def test_password_reset_rate_limited(self):
        for i in range(6):
            response = self.client.post("/en/accounts/password-reset/", {"email": f"nobody{i}@example.com"})
        self.assertEqual(response.status_code, 403)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email="profile@example.com", password="Str0ngPass!1")

    def test_profile_requires_login(self):
        response = self.client.get("/en/accounts/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_profile_updates_preferences_and_profile_forms(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/en/accounts/profile/",
            {
                "preferences-phone_number": "9811111111",
                "preferences-preferred_language": "ne",
                "profile-display_name": "Test User",
                "profile-bio": "A bio.",
            },
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "9811111111")
        self.assertEqual(self.user.profile.display_name, "Test User")
