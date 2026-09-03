from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.processes import services
from apps.processes.tests.factories import ProcessFactory, ProcessSourceFactory


class SitemapTests(TestCase):
    def test_sitemap_lists_published_processes_only(self):
        publisher = UserFactory()
        published = ProcessFactory(slug="published-process")
        ProcessSourceFactory(process=published)
        services.publish_new_version(published, publisher)
        draft = ProcessFactory(slug="draft-process")

        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/processes/published-process/")
        self.assertNotContains(response, "/processes/draft-process/")


class RobotsTxtTests(TestCase):
    def test_robots_txt_references_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertIn(b"Sitemap:", response.content)
        self.assertIn(b"/sitemap.xml", response.content)
