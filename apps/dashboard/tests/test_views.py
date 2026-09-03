import io
import shutil
import tempfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.accounts.tests.factories import UserFactory
from apps.dashboard.models import Notification, SavedProcess, UserDocument
from apps.processes import services as process_services
from apps.processes.tests.factories import ProcessFactory, ProcessSourceFactory
from apps.tasks.models import Task


def make_test_png(name="scan.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def publish(process, user):
    ProcessSourceFactory(process=process)
    process_services.publish_new_version(process, user)
    return process


class ToggleSavedViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.process = publish(ProcessFactory(), self.user)

    def test_requires_login(self):
        response = self.client.post(f"/en/dashboard/process/{self.process.slug}/save/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_toggle_saves_then_unsaves(self):
        self.client.force_login(self.user)
        url = f"/en/dashboard/process/{self.process.slug}/save/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SavedProcess.objects.filter(user=self.user, process=self.process).exists())

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SavedProcess.objects.filter(user=self.user, process=self.process).exists())

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/en/dashboard/process/{self.process.slug}/save/")
        self.assertEqual(response.status_code, 405)


class DeadlinesViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_requires_login(self):
        response = self.client.get("/en/dashboard/deadlines/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_defaults_to_upcoming_filter(self):
        today = date.today()
        Task.objects.create(user=self.user, title="Soon task", due_date=today + timedelta(days=3))
        Task.objects.create(user=self.user, title="Overdue task", due_date=today - timedelta(days=1))
        self.client.force_login(self.user)

        response = self.client.get("/en/dashboard/deadlines/")

        self.assertContains(response, "Soon task")
        self.assertNotContains(response, "Overdue task")

    def test_overdue_filter(self):
        today = date.today()
        Task.objects.create(user=self.user, title="Soon task", due_date=today + timedelta(days=3))
        Task.objects.create(user=self.user, title="Overdue task", due_date=today - timedelta(days=1))
        self.client.force_login(self.user)

        response = self.client.get("/en/dashboard/deadlines/", {"filter": "overdue"})

        self.assertContains(response, "Overdue task")
        self.assertNotContains(response, "Soon task")

    def test_completed_filter(self):
        today = date.today()
        Task.objects.create(user=self.user, title="Open task", due_date=today + timedelta(days=3))
        Task.objects.create(user=self.user, title="Finished task", due_date=today - timedelta(days=1), is_completed=True)
        self.client.force_login(self.user)

        response = self.client.get("/en/dashboard/deadlines/", {"filter": "completed"})

        self.assertContains(response, "Finished task")
        self.assertNotContains(response, "Open task")

    def test_invalid_filter_falls_back_to_upcoming(self):
        today = date.today()
        Task.objects.create(user=self.user, title="Soon task", due_date=today + timedelta(days=3))
        self.client.force_login(self.user)

        response = self.client.get("/en/dashboard/deadlines/", {"filter": "not-a-real-filter"})

        self.assertContains(response, "Soon task")

    def test_never_shows_another_users_deadline(self):
        other_user = UserFactory()
        Task.objects.create(user=other_user, title="Not yours", due_date=date.today() + timedelta(days=1))
        self.client.force_login(self.user)

        response = self.client.get("/en/dashboard/deadlines/")

        self.assertNotContains(response, "Not yours")


class NotificationsViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()

    def test_requires_login(self):
        response = self.client.get("/en/dashboard/notifications/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_never_shows_another_users_notification(self):
        Notification.objects.create(user=self.other_user, message="Not yours", dedupe_key="x")
        self.client.force_login(self.user)

        response = self.client.get("/en/dashboard/notifications/")

        self.assertNotContains(response, "Not yours")

    def test_mark_all_read_button_hidden_when_nothing_unread(self):
        Notification.objects.create(user=self.user, message="Read already", dedupe_key="x", is_read=True)
        self.client.force_login(self.user)

        response = self.client.get("/en/dashboard/notifications/")

        self.assertNotContains(response, "Mark all read")


class MarkNotificationReadViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()

    def test_requires_login(self):
        notification = Notification.objects.create(user=self.user, message="Hi", dedupe_key="x")
        response = self.client.post(f"/en/dashboard/notifications/{notification.id}/read/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_marks_own_notification_read(self):
        notification = Notification.objects.create(user=self.user, message="Hi", dedupe_key="x")
        self.client.force_login(self.user)

        response = self.client.post(f"/en/dashboard/notifications/{notification.id}/read/")

        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_cannot_mark_another_users_notification_read(self):
        notification = Notification.objects.create(user=self.other_user, message="Not yours", dedupe_key="x")
        self.client.force_login(self.user)

        response = self.client.post(f"/en/dashboard/notifications/{notification.id}/read/")

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)


class MarkAllNotificationsReadViewTests(TestCase):
    def test_requires_login(self):
        response = self.client.post("/en/dashboard/notifications/mark-all-read/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_only_marks_this_users_notifications(self):
        user = UserFactory()
        other_user = UserFactory()
        Notification.objects.create(user=user, message="A", dedupe_key="a")
        Notification.objects.create(user=other_user, message="B", dedupe_key="b")
        self.client.force_login(user)

        response = self.client.post("/en/dashboard/notifications/mark-all-read/")

        self.assertRedirects(response, "/en/dashboard/notifications/")
        self.assertTrue(Notification.objects.get(dedupe_key="a").is_read)
        self.assertFalse(Notification.objects.get(dedupe_key="b").is_read)


class DismissNotificationViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()

    def test_requires_login(self):
        notification = Notification.objects.create(user=self.user, message="Hi", dedupe_key="x")
        response = self.client.post(f"/en/dashboard/notifications/{notification.id}/dismiss/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_dismisses_own_notification(self):
        notification = Notification.objects.create(user=self.user, message="Hi", dedupe_key="x")
        self.client.force_login(self.user)

        response = self.client.post(f"/en/dashboard/notifications/{notification.id}/dismiss/")

        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_dismissed)

    def test_cannot_dismiss_another_users_notification(self):
        notification = Notification.objects.create(user=self.other_user, message="Not yours", dedupe_key="x")
        self.client.force_login(self.user)

        response = self.client.post(f"/en/dashboard/notifications/{notification.id}/dismiss/")

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_dismissed)


class DocumentCRUDViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()

    def test_create_requires_login(self):
        response = self.client.post(
            "/en/dashboard/documents/create/", {"document-title": "x", "document-document_type": "other"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_create_own_document(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/en/dashboard/documents/create/",
            {
                "document-title": "Citizenship certificate",
                "document-document_type": "citizenship",
                "document-expiry_date": (date.today() + timedelta(days=30)).isoformat(),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserDocument.objects.filter(user=self.user, title="Citizenship certificate").exists())

    def test_delete_own_document(self):
        document = UserDocument.objects.create(user=self.user, title="Mine")
        self.client.force_login(self.user)

        response = self.client.post(f"/en/dashboard/documents/{document.id}/delete/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserDocument.objects.filter(pk=document.id).exists())

    def test_cannot_delete_another_users_document(self):
        document = UserDocument.objects.create(user=self.other_user, title="Not yours")
        self.client.force_login(self.user)

        response = self.client.post(f"/en/dashboard/documents/{document.id}/delete/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(UserDocument.objects.filter(pk=document.id).exists())


class DocumentImageUploadTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.tmp_dir = tempfile.mkdtemp()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.tmp_dir)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)

    def test_create_document_with_image(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/en/dashboard/documents/create/",
            {
                "document-title": "Passport scan",
                "document-document_type": "passport",
                "document-image": make_test_png(),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        document = UserDocument.objects.get(user=self.user, title="Passport scan")
        self.assertTrue(document.image)

    def test_uploaded_image_is_not_a_valid_image_rejects(self):
        self.client.force_login(self.user)
        not_an_image = SimpleUploadedFile("scan.png", b"not a real image", content_type="image/png")

        response = self.client.post(
            "/en/dashboard/documents/create/",
            {"document-title": "Bad upload", "document-document_type": "other", "document-image": not_an_image},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserDocument.objects.filter(user=self.user, title="Bad upload").exists())

    def test_file_view_requires_login(self):
        document = UserDocument.objects.create(user=self.user, title="Mine", image=make_test_png())
        response = self.client.get(f"/en/dashboard/documents/{document.id}/file/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_owner_can_fetch_the_file(self):
        document = UserDocument.objects.create(user=self.user, title="Mine", image=make_test_png())
        self.client.force_login(self.user)

        response = self.client.get(f"/en/dashboard/documents/{document.id}/file/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content)[:8], b"\x89PNG\r\n\x1a\n")

    def test_cannot_fetch_another_users_file(self):
        document = UserDocument.objects.create(user=self.other_user, title="Not yours", image=make_test_png())
        self.client.force_login(self.user)

        response = self.client.get(f"/en/dashboard/documents/{document.id}/file/")

        self.assertEqual(response.status_code, 404)

    def test_404_when_document_has_no_image(self):
        document = UserDocument.objects.create(user=self.user, title="No scan")
        self.client.force_login(self.user)

        response = self.client.get(f"/en/dashboard/documents/{document.id}/file/")

        self.assertEqual(response.status_code, 404)


class DashboardViewOwnershipTests(TestCase):
    def test_dashboard_never_shows_another_users_saved_process(self):
        user = UserFactory()
        other_user = UserFactory()
        process = publish(ProcessFactory(title="Someone else's saved process"), other_user)
        SavedProcess.objects.create(user=other_user, process=process)

        self.client.force_login(user)
        response = self.client.get("/en/dashboard/")

        self.assertNotContains(response, "Someone else's saved process")

    def test_dashboard_never_shows_another_users_document(self):
        user = UserFactory()
        other_user = UserFactory()
        UserDocument.objects.create(user=other_user, title="Someone else's passport")

        self.client.force_login(user)
        response = self.client.get("/en/dashboard/")

        self.assertNotContains(response, "Someone else's passport")

    def test_dashboard_never_shows_another_users_notification(self):
        user = UserFactory()
        other_user = UserFactory()
        Notification.objects.create(user=other_user, message="Someone else's notification", dedupe_key="x")

        self.client.force_login(user)
        response = self.client.get("/en/dashboard/")

        self.assertNotContains(response, "Someone else's notification")
