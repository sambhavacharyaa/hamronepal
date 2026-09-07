from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from apps.accounts.tests.factories import UserFactory
from apps.dashboard.models import UserDocument
from apps.tasks.models import Task

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


class CSRFEnforcementTests(TestCase):
    def test_post_without_csrf_token_is_rejected(self):
        user = UserFactory()
        task = Task.objects.create(user=user, title="A task")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        response = client.post(f"/en/tasks/{task.id}/toggle/")

        self.assertEqual(response.status_code, 403)
        task.refresh_from_db()
        self.assertFalse(task.is_completed)


@override_settings(CACHES=LOCMEM_CACHE)
class AdminLoginRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_admin_login_page_loads(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)

    def test_admin_login_is_rate_limited(self):
        for i in range(11):
            response = self.client.post(
                "/admin/login/",
                {"username": f"attacker{i}@example.com", "password": "guess"},
            )
        self.assertEqual(response.status_code, 403)

    def test_legitimate_superuser_can_still_log_in(self):
        superuser = UserFactory(email="admin@example.com", is_staff=True, is_superuser=True)

        response = self.client.post(
            "/admin/login/",
            {"username": superuser.email, "password": "Str0ngPass!1"},
        )

        self.assertEqual(response.status_code, 302)


class UserDocumentAdminPermissionTests(TestCase):
    def setUp(self):
        self.document_owner = UserFactory()
        self.document = UserDocument.objects.create(user=self.document_owner, title="A private passport scan")

    def test_non_superuser_staff_cannot_list_documents_even_with_permission_granted(self):
        staff_user = UserFactory(is_staff=True)
        staff_user.user_permissions.add(*Permission.objects.filter(content_type__app_label="dashboard"))
        self.client.force_login(staff_user)

        response = self.client.get("/admin/dashboard/userdocument/")

        self.assertEqual(response.status_code, 403)

    def test_non_superuser_staff_cannot_view_document_detail(self):
        staff_user = UserFactory(is_staff=True)
        self.client.force_login(staff_user)

        response = self.client.get(f"/admin/dashboard/userdocument/{self.document.pk}/change/")

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_list_documents(self):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_login(superuser)

        response = self.client.get("/admin/dashboard/userdocument/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A private passport scan")
