import re

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.templatetags.static import static
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve
from django_ratelimit.decorators import ratelimit

from apps.core.views import robots_txt_view
from apps.processes.sitemaps import ProcessSitemap, StaticViewSitemap
from apps.tourism.sitemaps import DestinationSitemap

sitemaps = {
    "processes": ProcessSitemap,
    "tourism": DestinationSitemap,
    "static": StaticViewSitemap,
}


@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def admin_login_view(request, *args, **kwargs):
    return admin.site.login(request, *args, **kwargs)


urlpatterns = [
    path("admin/login/", admin_login_view, name="admin_login_ratelimited"),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", robots_txt_view, name="robots_txt"),
    path(
        "favicon.ico",
        RedirectView.as_view(url=static("img/favicon/favicon.ico"), permanent=True),
    ),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]

urlpatterns += [
    re_path(
        r"^%s(?P<path>.*)$" % re.escape(settings.MEDIA_URL.lstrip("/")),
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]

urlpatterns += i18n_patterns(
    path("", include("apps.core.urls")),
    path("", include("apps.processes.urls")),
    path("tourism/", include("apps.tourism.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
)
