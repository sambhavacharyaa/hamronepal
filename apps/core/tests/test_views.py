from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.processes import services
from apps.processes.tests.factories import ProcessCategoryFactory, ProcessFactory, ProcessSourceFactory
from apps.tasks.models import Task


class HomeViewTests(TestCase):
    def test_home_renders_with_no_processes_yet(self):
        response = self.client.get("/en/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "start here")

    def test_situation_tiles_show_honest_counts(self):
        user = UserFactory()
        business = ProcessCategoryFactory(name="Business", slug="business")
        travel = ProcessCategoryFactory(name="Travel", slug="travel-documents")
        for title in ["Register a company", "Get a PAN"]:
            process = ProcessFactory(title=title, category=business)
            ProcessSourceFactory(process=process)
            services.publish_new_version(process, user)
        process = ProcessFactory(title="Apply for a passport", category=travel)
        ProcessSourceFactory(process=process)
        services.publish_new_version(process, user)

        response = self.client.get("/en/")

        self.assertContains(response, "starting a business")
        self.assertContains(response, "2 processes")
        self.assertContains(response, "going abroad")
        self.assertContains(response, "1 process")
        self.assertContains(response, "Not covered yet")

    def test_situation_tile_with_results_leads_to_real_content(self):
        user = UserFactory()
        business = ProcessCategoryFactory(name="Business", slug="business")
        process = ProcessFactory(title="Register a company", category=business)
        ProcessSourceFactory(process=process)
        services.publish_new_version(process, user)

        tile_url = services.get_homepage_situations()[0]["url"]

        list_response = self.client.get(tile_url)
        self.assertContains(list_response, "Register a company")

    def test_coverage_line_reflects_real_published_count(self):
        user = UserFactory()
        process = ProcessFactory(title="A real process")
        ProcessSourceFactory(process=process)
        services.publish_new_version(process, user)

        response = self.client.get("/en/")

        self.assertContains(response, "1 process today")

    def test_catalog_region_lists_published_processes(self):
        user = UserFactory()
        process = ProcessFactory(title="Register a company")
        ProcessSourceFactory(process=process)
        services.publish_new_version(process, user)

        response = self.client.get("/en/")

        self.assertContains(response, "Register a company")

    def test_trust_block_shows_real_freshness_number(self):
        user = UserFactory()
        process = ProcessFactory(title="Register a company")
        ProcessSourceFactory(process=process)
        services.publish_new_version(process, user)

        response = self.client.get("/en/")

        self.assertContains(response, "checked against an official source")
        self.assertContains(response, "0 days")

    def test_trust_block_handles_no_sources_yet(self):
        response = self.client.get("/en/")

        self.assertContains(response, "No sources checked yet.")

    def test_resume_strip_shows_for_user_with_active_progress(self):
        user = UserFactory()
        process = ProcessFactory(title="Register a company")
        ProcessSourceFactory(process=process)
        services.publish_new_version(process, user)
        services.start_tracking(user, process, None)

        self.client.force_login(user)
        response = self.client.get("/en/")

        self.assertContains(response, "Continue where you left off")
        self.assertContains(response, "Register a company")
        self.assertNotContains(response, "What makes this trustworthy")

    def test_no_resume_strip_without_active_progress(self):
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get("/en/")

        self.assertNotContains(response, "Continue where you left off")
        self.assertContains(response, "checked against an official source")


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_dashboard_requires_login(self):
        response = self.client.get("/en/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_empty_dashboard_shows_empty_states(self):
        self.client.force_login(self.user)
        response = self.client.get("/en/dashboard/")
        self.assertContains(response, "not tracking any processes")
        self.assertContains(response, "Nothing needs your attention right now.")

    def test_dashboard_shows_active_process_and_task(self):
        process = ProcessFactory(title="Trackable Process")
        ProcessSourceFactory(process=process)
        services.publish_new_version(process, self.user)
        services.start_tracking(self.user, process, None)
        Task.objects.create(user=self.user, title="A pending task")

        self.client.force_login(self.user)
        response = self.client.get("/en/dashboard/")

        self.assertContains(response, "Trackable Process")
        self.assertContains(response, "A pending task")
