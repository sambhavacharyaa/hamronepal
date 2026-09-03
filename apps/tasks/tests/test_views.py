from datetime import date, timedelta

from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.tasks.models import Task


class TaskCRUDTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.client.force_login(self.user)

    def test_create_task(self):
        response = self.client.post(
            "/en/tasks/create/",
            {"title": "Renew passport", "due_date": (date.today() + timedelta(days=5)).isoformat()},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Task.objects.filter(user=self.user, title="Renew passport").exists())

    def test_create_task_requires_login(self):
        self.client.logout()
        response = self.client.post("/en/tasks/create/", {"title": "x"})
        self.assertEqual(response.status_code, 302)

    def test_toggle_task_via_htmx(self):
        task = Task.objects.create(user=self.user, title="A task")
        response = self.client.post(f"/en/tasks/{task.id}/toggle/", HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertTrue(task.is_completed)

    def test_cannot_toggle_another_users_task(self):
        task = Task.objects.create(user=self.other_user, title="Not yours")
        response = self.client.post(f"/en/tasks/{task.id}/toggle/")
        self.assertEqual(response.status_code, 404)

    def test_delete_own_task(self):
        task = Task.objects.create(user=self.user, title="Delete me")
        response = self.client.post(f"/en/tasks/{task.id}/delete/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(pk=task.id).exists())

    def test_cannot_delete_another_users_task(self):
        task = Task.objects.create(user=self.other_user, title="Not yours")
        response = self.client.post(f"/en/tasks/{task.id}/delete/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Task.objects.filter(pk=task.id).exists())
