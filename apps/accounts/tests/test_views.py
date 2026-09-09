import io
import re
import shutil
import tempfile

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.models import Profile, User

from .factories import UserFactory


def make_test_png(name="avatar.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color="blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def _extract_url(body):
    match = re.search(r"https?://\S+", body)
    assert match, body
    return match.group(0)


def _register_payload(**overrides):
    payload = {
        "email": "newuser@example.com",
        "password1": "S0meStrongPass!",
        "password2": "S0meStrongPass!",
        "agree_to_terms": "on",
    }
    payload.update(overrides)
    return payload


@override_settings(CACHES=LOCMEM_CACHE)
class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_get_register_page(self):
        response = self.client.get("/en/accounts/register/")
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_logs_in_and_sends_verification_email(self):
        response = self.client.post(
            "/en/accounts/register/",
            _register_payload(email="newuser@example.com", phone_number="9800000000"),
        )

        self.assertRedirects(response, reverse("core:dashboard"))
        user = User.objects.get(email="newuser@example.com")
        self.assertFalse(user.email_verified)
        self.assertIsNotNone(user.terms_accepted_at)
        self.assertEqual(len(mail.outbox), 1)

    def test_register_requires_agreeing_to_terms(self):
        payload = _register_payload(email="noconsent@example.com")
        del payload["agree_to_terms"]

        response = self.client.post("/en/accounts/register/", payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="noconsent@example.com").exists())

    def test_verification_link_marks_user_verified_and_is_idempotent(self):
        self.client.post("/en/accounts/register/", _register_payload(email="verify@example.com"))
        user = User.objects.get(email="verify@example.com")
        verify_path = _extract_url(mail.outbox[0].body).split("testserver", 1)[1]
        self.client.logout()

        self.client.get(verify_path)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

        self.client.get(verify_path)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_registration_rate_limited(self):
        for i in range(11):
            response = self.client.post(
                "/en/accounts/register/",
                _register_payload(email=f"rl{i}@example.com"),
            )
        self.assertEqual(response.status_code, 403)


@override_settings(CACHES=LOCMEM_CACHE)
class ResendVerificationTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_requires_login(self):
        response = self.client.post("/en/accounts/verify-email/resend/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_get_not_allowed(self):
        self.client.force_login(UserFactory(email_verified=False))
        response = self.client.get("/en/accounts/verify-email/resend/")
        self.assertEqual(response.status_code, 405)

    def test_sends_a_new_verification_email_for_unverified_user(self):
        user = UserFactory(email="unverified@example.com", email_verified=False)
        self.client.force_login(user)

        response = self.client.post("/en/accounts/verify-email/resend/", follow=True)

        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].to)

    def test_new_link_still_verifies_the_user(self):
        user = UserFactory(email="unverified2@example.com", email_verified=False)
        self.client.force_login(user)
        self.client.post("/en/accounts/verify-email/resend/")
        verify_path = _extract_url(mail.outbox[0].body).split("testserver", 1)[1]

        self.client.get(verify_path)

        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_already_verified_user_does_not_get_another_email(self):
        user = UserFactory(email="already@example.com", email_verified=True)
        self.client.force_login(user)

        self.client.post("/en/accounts/verify-email/resend/")

        self.assertEqual(len(mail.outbox), 0)

    def test_resend_is_rate_limited(self):
        user = UserFactory(email_verified=False)
        self.client.force_login(user)

        for i in range(6):
            response = self.client.post("/en/accounts/verify-email/resend/")

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


@override_settings(CACHES=LOCMEM_CACHE)
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
                "preferences-preferred_language": "np",
                "profile-display_name": "Test User",
                "profile-bio": "A bio.",
            },
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "9811111111")
        self.assertEqual(self.user.profile.display_name, "Test User")


class ProfileAvatarTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email="avatar-owner@example.com", password="Str0ngPass!1")
        self.client.force_login(self.user)
        self.tmp_dir = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.tmp_dir)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)

    def _base_payload(self, **overrides):
        payload = {
            "preferences-phone_number": "",
            "preferences-preferred_language": "en",
            "profile-display_name": "",
            "profile-bio": "",
        }
        payload.update(overrides)
        return payload

    def test_uploading_an_avatar_saves_it(self):
        response = self.client.post(
            "/en/accounts/profile/",
            self._base_payload(**{"profile-avatar": make_test_png()}),
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.avatar)

    def test_saving_without_a_new_file_keeps_the_existing_avatar(self):
        Profile.objects.create(user=self.user, avatar=make_test_png())

        self.client.post("/en/accounts/profile/", self._base_payload(**{"profile-display_name": "Someone"}))

        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.avatar)

    def test_remove_photo_clears_the_avatar(self):
        Profile.objects.create(user=self.user, avatar=make_test_png())

        self.client.post("/en/accounts/profile/", self._base_payload(**{"profile-remove_avatar": "on"}))

        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)

    def test_uploading_a_new_file_wins_over_a_stray_remove_flag(self):
        Profile.objects.create(user=self.user, avatar=make_test_png("old.png"))

        self.client.post(
            "/en/accounts/profile/",
            self._base_payload(**{"profile-remove_avatar": "on", "profile-avatar": make_test_png("new.png")}),
        )

        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.avatar)
        self.assertIn("new", self.user.profile.avatar.name)
