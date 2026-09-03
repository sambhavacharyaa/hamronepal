from django.test import TestCase

from apps.accounts.models import User


class UserManagerTests(TestCase):
    def test_create_user_normalizes_email_and_sets_password(self):
        user = User.objects.create_user(email="Person@Example.com", password="Str0ngPass!1")

        self.assertEqual(user.email, "Person@example.com")
        self.assertTrue(user.check_password("Str0ngPass!1"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.email_verified)

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="Str0ngPass!1")

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        user = User.objects.create_superuser(email="admin@example.com", password="Str0ngPass!1")

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_rejects_is_staff_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="admin@example.com", password="x", is_staff=False)

    def test_user_str_is_email(self):
        user = User.objects.create_user(email="person@example.com", password="x")
        self.assertEqual(str(user), "person@example.com")
