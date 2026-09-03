from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.tasks import services
from apps.tasks.models import Task


class ToggleCompletedTests(TestCase):
    def setUp(self):
        self.task = Task.objects.create(user=UserFactory(), title="Renew passport")

    def test_toggle_marks_completed_and_stamps_time(self):
        task = services.toggle_completed(self.task)
        self.assertTrue(task.is_completed)
        self.assertIsNotNone(task.completed_at)

    def test_toggle_again_reverts(self):
        services.toggle_completed(self.task)
        task = services.toggle_completed(self.task)
        self.assertFalse(task.is_completed)
        self.assertIsNone(task.completed_at)
