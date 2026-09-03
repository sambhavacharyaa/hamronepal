from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.dashboard.models import Notification


class NotificationsContextProcessorTests(TestCase):
    def test_navbar_shows_bell_with_unread_count_for_logged_in_user(self):
        user = UserFactory()
        Notification.objects.create(user=user, message="Hi", dedupe_key="a")
        Notification.objects.create(user=user, message="Hi again", dedupe_key="b", is_read=True)
        self.client.force_login(user)

        response = self.client.get("/en/")

        self.assertContains(response, 'id="navbar-notification-badge"')
        self.assertContains(response, 'href="/en/dashboard/notifications/"')

    def test_navbar_hides_bell_for_anonymous_user(self):
        response = self.client.get("/en/")

        self.assertNotContains(response, "dashboard/notifications/")

    def test_navbar_badge_reflects_only_this_users_unread_count(self):
        user = UserFactory()
        other_user = UserFactory()
        Notification.objects.create(user=user, message="Mine", dedupe_key="a")
        Notification.objects.create(user=other_user, message="Not mine", dedupe_key="b")
        Notification.objects.create(user=other_user, message="Also not mine", dedupe_key="c")
        self.client.force_login(user)

        response = self.client.get("/en/")

        self.assertEqual(response.context["nav_unread_notification_count"], 1)
