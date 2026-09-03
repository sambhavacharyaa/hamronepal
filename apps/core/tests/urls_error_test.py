from django.urls import path

from config.urls import urlpatterns as base_urlpatterns


def _broken_view(request):
    raise RuntimeError("Deliberate error for testing the custom 500 page.")


urlpatterns = [*base_urlpatterns, path("__test-500__/", _broken_view)]
