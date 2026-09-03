from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.processes import services
from apps.processes.models import Process, ProcessVariant

from .factories import (
    ProcessCategoryFactory,
    ProcessFactory,
    ProcessFAQFactory,
    ProcessRequirementFactory,
    ProcessSourceFactory,
    ProcessStepFactory,
)


def _publish(process, user):
    ProcessSourceFactory(process=process)
    services.publish_new_version(process, user)


class SearchViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category = ProcessCategoryFactory()
        self.published = ProcessFactory(
            title="Company Registration in Nepal", category=self.category,
            summary="Register a company with the Office of the Company Registrar.",
        )
        _publish(self.published, self.user)
        self.draft = ProcessFactory(title="Draft Company Renewal", category=self.category)

    def test_search_finds_published_process_and_excludes_draft(self):
        response = self.client.get("/en/search/", {"q": "company registration"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Company Registration in Nepal")
        self.assertNotContains(response, "Draft Company Renewal")

    def test_htmx_request_returns_bare_partial(self):
        response = self.client.get("/en/search/", {"q": "company registration"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"<html", response.content)
        self.assertContains(response, "Company Registration in Nepal")

    def test_no_query_shows_full_catalog(self):
        response = self.client.get("/en/search/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Company Registration in Nepal")
        self.assertNotContains(response, "Draft Company Renewal")

    def test_no_match_shows_empty_state(self):
        response = self.client.get("/en/search/", {"q": "nonexistent-xyz-term"})
        self.assertContains(response, "No processes found")


class ProcessListViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category_a = ProcessCategoryFactory(name="Business", slug="business")
        self.category_b = ProcessCategoryFactory(name="Travel", slug="travel")
        self.process_a = ProcessFactory(title="Process A", category=self.category_a)
        self.process_b = ProcessFactory(title="Process B", category=self.category_b)
        _publish(self.process_a, self.user)
        _publish(self.process_b, self.user)

    def test_list_shows_all_published_processes(self):
        response = self.client.get("/en/processes/")
        self.assertContains(response, "Process A")
        self.assertContains(response, "Process B")

    def test_category_filter(self):
        response = self.client.get("/en/processes/", {"category": "business"})
        self.assertContains(response, "Process A")
        self.assertNotContains(response, "Process B")


class VerifiedBadgeTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category = ProcessCategoryFactory()

    def test_published_process_with_verification_date_shows_badge(self):
        process = ProcessFactory(title="Verified Process", category=self.category)
        _publish(process, self.user)

        response = self.client.get("/en/processes/")

        self.assertContains(response, "Verified Process")
        self.assertContains(response, "Verified")

    def test_published_process_without_verification_date_hides_badge(self):
        process = ProcessFactory(title="Unverified Process", category=self.category)
        _publish(process, self.user)
        Process.objects.filter(pk=process.pk).update(last_verified_at=None)

        response = self.client.get("/en/processes/")

        self.assertContains(response, "Unverified Process")
        self.assertNotContains(response, "Verified")


class PriceTagAndSourceReceiptTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.category = ProcessCategoryFactory()

    def test_card_shows_duration_fee_and_counts(self):
        process = ProcessFactory(
            title="Register for a PAN",
            category=self.category,
            estimated_duration_min_days=1,
            estimated_duration_max_days=3,
            total_fee_note="Free",
        )
        ProcessStepFactory(process=process, order=1)
        ProcessStepFactory(process=process, order=2)
        ProcessRequirementFactory(process=process, order=1)
        _publish(process, self.user)

        response = self.client.get("/en/processes/")

        self.assertContains(response, "1-3 days")
        self.assertContains(response, "Free")
        self.assertContains(response, "2 steps")
        self.assertContains(response, "1 document")

    def test_card_source_receipt_links_to_real_government_url(self):
        process = ProcessFactory(title="Register for a PAN", category=self.category)
        ProcessSourceFactory(
            process=process, title="Inland Revenue Department", url="https://ird.gov.np/"
        )
        services.publish_new_version(process, self.user)

        response = self.client.get("/en/processes/")

        self.assertContains(response, "https://ird.gov.np/")
        self.assertContains(response, "Inland Revenue Department")

    def test_card_hides_receipt_disclosure_when_not_verified(self):
        process = ProcessFactory(title="Unverified Process", category=self.category)
        _publish(process, self.user)
        Process.objects.filter(pk=process.pk).update(last_verified_at=None)

        response = self.client.get("/en/processes/")

        self.assertNotContains(response, '<details class="relative z-10')


class ProcessDetailViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.process = ProcessFactory(title="Apply for a Thing")
        ProcessStepFactory(process=self.process, order=1, title="First step")
        ProcessFAQFactory(process=self.process, question="A question?")
        _publish(self.process, self.user)
        self.draft = ProcessFactory(title="Draft Thing")

    def test_published_process_renders_with_json_ld(self):
        response = self.client.get(f"/en/processes/{self.process.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "application/ld+json")
        self.assertContains(response, '"@type": "HowTo"')
        self.assertContains(response, '"@type": "FAQPage"')

    def test_draft_process_404s(self):
        response = self.client.get(f"/en/processes/{self.draft.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_anonymous_sees_login_prompt_not_start_form(self):
        response = self.client.get(f"/en/processes/{self.process.slug}/")
        self.assertContains(response, "Log in")
        self.assertNotContains(response, "Start tracking")

    def test_authenticated_sees_start_form(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/en/processes/{self.process.slug}/")
        self.assertContains(response, "Start tracking")

    def test_hreflang_alternates_present(self):
        response = self.client.get(f"/en/processes/{self.process.slug}/")
        self.assertContains(response, 'hreflang="en"')
        self.assertContains(response, 'hreflang="np"')


class TrackingFlowTests(TestCase):
    def setUp(self):
        self.publisher = UserFactory()
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.process = ProcessFactory()
        self.step = ProcessStepFactory(process=self.process, order=1)
        self.requirement = ProcessRequirementFactory(process=self.process, order=1)
        _publish(self.process, self.publisher)

    def test_start_tracking_requires_login(self):
        response = self.client.post(f"/en/processes/{self.process.slug}/start/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_start_tracking_requires_variant_when_process_has_variants(self):
        ProcessStepFactory(process=self.process, order=2, variant=ProcessVariant.BUSINESS)
        self.client.force_login(self.user)

        response = self.client.post(f"/en/processes/{self.process.slug}/start/", follow=True)

        from apps.processes.models import UserProcessProgress

        self.assertFalse(UserProcessProgress.objects.filter(user=self.user, process=self.process).exists())

    def test_start_tracking_redirects_to_track_progress(self):
        self.client.force_login(self.user)
        response = self.client.post(f"/en/processes/{self.process.slug}/start/")
        self.assertRedirects(response, f"/en/processes/{self.process.slug}/track/")

    def test_track_progress_requires_login(self):
        response = self.client.get(f"/en/processes/{self.process.slug}/track/")
        self.assertEqual(response.status_code, 302)

    def test_track_progress_404s_for_a_user_not_tracking_it(self):
        self.client.force_login(self.other_user)
        response = self.client.get(f"/en/processes/{self.process.slug}/track/")
        self.assertEqual(response.status_code, 404)

    def test_toggle_step_via_htmx(self):
        self.client.force_login(self.user)
        self.client.post(f"/en/processes/{self.process.slug}/start/")

        response = self.client.post(
            f"/en/processes/{self.process.slug}/track/step/{self.step.id}/toggle/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"<html", response.content)

    def test_toggle_step_requires_login(self):
        response = self.client.post(f"/en/processes/{self.process.slug}/track/step/{self.step.id}/toggle/")
        self.assertEqual(response.status_code, 302)

    def test_advance_status_updates_progress(self):
        self.client.force_login(self.user)
        self.client.post(f"/en/processes/{self.process.slug}/start/")

        response = self.client.post(
            f"/en/processes/{self.process.slug}/track/advance/", {"status": "applied"}, follow=True
        )
        self.assertEqual(response.status_code, 200)

        from apps.processes.models import UserProcessProgress

        progress = UserProcessProgress.objects.get(user=self.user, process=self.process)
        self.assertEqual(progress.status, UserProcessProgress.Status.APPLIED)
