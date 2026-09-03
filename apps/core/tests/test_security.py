from django.test import Client, TestCase

from apps.accounts.tests.factories import UserFactory
from apps.tasks.models import Task


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
