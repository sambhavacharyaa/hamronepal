from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.processes import services
from apps.processes.models import UserProcessProgress

from .factories import ProcessFactory, ProcessRequirementFactory, ProcessSourceFactory, ProcessStepFactory


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
)
class AnonymousToCompletedSmokeTest(TestCase):
    def setUp(self):
        publisher = User.objects.create_superuser(email="publisher@example.com", password="x")
        self.process = ProcessFactory(title="Register a Test Company", slug="register-a-test-company")
        self.step = ProcessStepFactory(process=self.process, order=1, title="Reserve a name")
        self.requirement = ProcessRequirementFactory(process=self.process, order=1, name="Citizenship copy")
        ProcessSourceFactory(process=self.process)
        services.publish_new_version(self.process, publisher)

    def test_full_journey(self):
        client = self.client

        # 1. Anonymous discovery via search from the homepage.
        response = client.get("/en/")
        self.assertEqual(response.status_code, 200)

        response = client.get("/en/search/", {"q": "test company"})
        self.assertContains(response, "Register a Test Company")

        # 2. View the process detail page — full content visible, no start form yet.
        response = client.get(f"/en/processes/{self.process.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reserve a name")
        self.assertNotContains(response, "Start tracking")

        # 3. Register.
        response = client.post(
            "/en/accounts/register/",
            {"email": "traveler@example.com", "password1": "S0meStrongPass!", "password2": "S0meStrongPass!"},
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertEqual(len(mail.outbox), 1)

        # 4. Back on the process page, now logged in — the start form appears.
        response = client.get(f"/en/processes/{self.process.slug}/")
        self.assertContains(response, "Start tracking")

        # 5. Start tracking.
        response = client.post(f"/en/processes/{self.process.slug}/start/")
        self.assertRedirects(response, f"/en/processes/{self.process.slug}/track/")

        user = User.objects.get(email="traveler@example.com")
        progress = UserProcessProgress.objects.get(user=user, process=self.process)
        self.assertEqual(progress.status, UserProcessProgress.Status.NOT_STARTED)

        # 6. Appears on the dashboard as active.
        response = client.get("/en/dashboard/")
        self.assertContains(response, "Register a Test Company")

        # 7. Check off the step and the requirement.
        client.post(f"/en/processes/{self.process.slug}/track/step/{self.step.id}/toggle/")
        client.post(f"/en/processes/{self.process.slug}/track/requirement/{self.requirement.id}/toggle/")

        progress.refresh_from_db()
        self.assertEqual(progress.status, UserProcessProgress.Status.PREPARING)
        self.assertEqual(services.compute_percent(progress), 100)

        # 8. Advance through the real-world milestones to completion.
        client.post(f"/en/processes/{self.process.slug}/track/advance/", {"status": "applied"})
        client.post(f"/en/processes/{self.process.slug}/track/advance/", {"status": "processing"})
        response = client.post(f"/en/processes/{self.process.slug}/track/advance/", {"status": "completed"})
        self.assertEqual(response.status_code, 302)

        progress.refresh_from_db()
        self.assertEqual(progress.status, UserProcessProgress.Status.COMPLETED)
        self.assertIsNotNone(progress.completed_at)

        # 9. Completed process drops off the active journeys list.
        response = client.get("/en/dashboard/")
        self.assertContains(response, "Register a Test Company", count=2)
        self.assertContains(response, "not tracking any processes yet")
