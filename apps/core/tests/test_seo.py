from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.core.seo import build_breadcrumb_json_ld, build_organization_json_ld, to_json_ld_script
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

    def test_sitemap_includes_hreflang_alternates(self):
        publisher = UserFactory()
        published = ProcessFactory(slug="published-process")
        ProcessSourceFactory(process=published)
        services.publish_new_version(published, publisher)

        response = self.client.get("/sitemap.xml")

        self.assertContains(response, 'hreflang="en"')
        self.assertContains(response, 'hreflang="np"')
        self.assertContains(response, 'hreflang="x-default"')


class RobotsTxtTests(TestCase):
    def test_robots_txt_references_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertIn(b"Sitemap:", response.content)
        self.assertIn(b"/sitemap.xml", response.content)

    def test_robots_txt_only_disallows_admin(self):
        response = self.client.get("/robots.txt")
        self.assertIn(b"Disallow: /admin/", response.content)
        self.assertNotIn(b"Disallow: /accounts/", response.content)
        self.assertNotIn(b"Disallow: /dashboard/", response.content)


class MetaTagsTests(TestCase):
    def test_home_has_canonical_and_hreflang(self):
        response = self.client.get("/en/")
        self.assertContains(response, '<link rel="canonical" href="http://testserver/en/">')
        self.assertContains(response, 'hreflang="en"')
        self.assertContains(response, 'hreflang="np"')
        self.assertContains(response, 'hreflang="x-default"')

    def test_home_has_open_graph_and_twitter_tags(self):
        response = self.client.get("/en/")
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, 'property="og:image"')
        self.assertContains(response, 'name="twitter:card"')

    def test_canonical_strips_query_string(self):
        response = self.client.get("/en/processes/?category=business")
        self.assertContains(response, '<link rel="canonical" href="http://testserver/en/processes/">')

    def test_public_page_is_indexable(self):
        response = self.client.get("/en/")
        self.assertContains(response, '<meta name="robots" content="index, follow">')

    def test_search_with_query_is_noindex(self):
        response = self.client.get("/en/search/", {"q": "passport"})
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')

    def test_organization_json_ld_present(self):
        response = self.client.get("/en/")
        self.assertContains(response, '"@type": "Organization"')


class NoindexHeaderTests(TestCase):
    def test_dashboard_is_noindexed(self):
        response = self.client.get("/en/dashboard/")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")

    def test_accounts_login_is_noindexed(self):
        response = self.client.get("/en/accounts/login/")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")

    def test_public_home_is_not_noindexed(self):
        response = self.client.get("/en/")
        self.assertNotIn("X-Robots-Tag", response)

    def test_public_process_detail_is_not_noindexed(self):
        publisher = UserFactory()
        process = ProcessFactory(slug="a-process")
        ProcessSourceFactory(process=process)
        services.publish_new_version(process, publisher)

        response = self.client.get("/en/processes/a-process/")

        self.assertNotIn("X-Robots-Tag", response)


class ProcessDetailBreadcrumbTests(TestCase):
    def test_breadcrumb_json_ld_present(self):
        publisher = UserFactory()
        process = ProcessFactory(slug="a-process", title="A Process")
        ProcessSourceFactory(process=process)
        services.publish_new_version(process, publisher)

        response = self.client.get("/en/processes/a-process/")

        self.assertContains(response, '"@type": "BreadcrumbList"')
        self.assertContains(response, "A Process")


class SeoBuilderTests(TestCase):
    def test_build_breadcrumb_json_ld_shape(self):
        data = build_breadcrumb_json_ld([("Home", "https://example.com/"), ("Page", "https://example.com/page/")])
        self.assertEqual(data["@type"], "BreadcrumbList")
        self.assertEqual(len(data["itemListElement"]), 2)
        self.assertEqual(data["itemListElement"][0]["position"], 1)
        self.assertEqual(data["itemListElement"][0]["name"], "Home")

    def test_breadcrumb_accepts_lazy_translated_names(self):
        from django.utils.translation import gettext_lazy as _

        data = build_breadcrumb_json_ld([(_("Home"), "https://example.com/")])
        script = to_json_ld_script(data)
        self.assertIn("Home", str(script))

    def test_build_organization_json_ld_uses_request_host(self):
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        data = build_organization_json_ld(request)
        self.assertEqual(data["@type"], "Organization")
        self.assertTrue(data["url"].startswith("http://testserver/"))
