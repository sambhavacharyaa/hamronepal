from django.test import Client, TestCase, override_settings


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class NotFoundPageTests(TestCase):
    def test_custom_404_renders(self):
        response = self.client.get("/en/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)


@override_settings(
    DEBUG=False,
    ALLOWED_HOSTS=["testserver"],
    ROOT_URLCONF="apps.core.tests.urls_error_test",
)
class ServerErrorPageTests(TestCase):
    def test_custom_500_renders(self):
        client = Client(raise_request_exception=False)
        response = client.get("/__test-500__/")
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Something went wrong", status_code=500)
