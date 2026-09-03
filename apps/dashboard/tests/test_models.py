from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.dashboard.models import Notification, RecentlyViewedProcess, SavedProcess, UserDocument
from apps.processes.tests.factories import ProcessFactory
from apps.tasks.models import Task


class SavedProcessModelTests(TestCase):
    def test_str(self):
        user = UserFactory(email="traveler@example.com")
        process = ProcessFactory(title="Apply for a passport")
        saved = SavedProcess.objects.create(user=user, process=process)
        self.assertIn("traveler@example.com", str(saved))
        self.assertIn("Apply for a passport", str(saved))

    def test_user_cannot_save_same_process_twice(self):
        user = UserFactory()
        process = ProcessFactory()
        SavedProcess.objects.create(user=user, process=process)
        with self.assertRaises(IntegrityError):
            SavedProcess.objects.create(user=user, process=process)

    def test_version_at_save_defaults_blank(self):
        saved = SavedProcess.objects.create(user=UserFactory(), process=ProcessFactory())
        self.assertEqual(saved.version_at_save, "")


class RecentlyViewedProcessModelTests(TestCase):
    def test_user_cannot_have_duplicate_recently_viewed_rows(self):
        user = UserFactory()
        process = ProcessFactory()
        RecentlyViewedProcess.objects.create(user=user, process=process)
        with self.assertRaises(IntegrityError):
            RecentlyViewedProcess.objects.create(user=user, process=process)


class UserDocumentModelTests(TestCase):
    def test_str_is_title(self):
        document = UserDocument.objects.create(user=UserFactory(), title="Citizenship certificate")
        self.assertEqual(str(document), "Citizenship certificate")

    def test_default_document_type_is_other(self):
        document = UserDocument.objects.create(user=UserFactory(), title="Something")
        self.assertEqual(document.document_type, UserDocument.DocumentType.OTHER)


class NotificationModelTests(TestCase):
    def test_str_is_message(self):
        notification = Notification.objects.create(
            user=UserFactory(), message="Your passport expires soon.", dedupe_key="a"
        )
        self.assertEqual(str(notification), "Your passport expires soon.")

    def test_dedupe_key_is_unique_per_user(self):
        user = UserFactory()
        Notification.objects.create(user=user, message="First", dedupe_key="document_expiry_1")
        with self.assertRaises(IntegrityError):
            Notification.objects.create(user=user, message="Second", dedupe_key="document_expiry_1")

    def test_same_dedupe_key_allowed_for_different_users(self):
        Notification.objects.create(user=UserFactory(), message="First", dedupe_key="document_expiry_1")
        Notification.objects.create(user=UserFactory(), message="Second", dedupe_key="document_expiry_1")
        self.assertEqual(Notification.objects.filter(dedupe_key="document_expiry_1").count(), 2)

    def test_defaults_to_not_dismissed(self):
        notification = Notification.objects.create(user=UserFactory(), message="Hi", dedupe_key="x")
        self.assertFalse(notification.is_dismissed)
        self.assertIsNone(notification.dismissed_at)

    def test_defaults_to_unread(self):
        notification = Notification.objects.create(user=UserFactory(), message="Hi", dedupe_key="x")
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_defaults_to_process_update_category(self):
        notification = Notification.objects.create(user=UserFactory(), message="Hi", dedupe_key="x")
        self.assertEqual(notification.category, Notification.Category.PROCESS_UPDATE)

    def test_email_and_push_sent_default_unset(self):
        notification = Notification.objects.create(user=UserFactory(), message="Hi", dedupe_key="x")
        self.assertIsNone(notification.email_sent_at)
        self.assertIsNone(notification.push_sent_at)

    def test_can_link_to_a_task_and_a_document(self):
        user = UserFactory()
        task = Task.objects.create(user=user, title="A task")
        document = UserDocument.objects.create(user=user, title="A document")
        notification = Notification.objects.create(
            user=user, message="Hi", dedupe_key="x", related_task=task, related_document=document
        )
        self.assertEqual(notification.related_task, task)
        self.assertEqual(notification.related_document, document)
