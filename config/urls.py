from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.core.views import robots_txt_view
from apps.processes.sitemaps import ProcessSitemap, StaticViewSitemap

sitemaps = {
    "processes": ProcessSitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", robots_txt_view, name="robots_txt"),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += i18n_patterns(
    path("", include("apps.core.urls")),
    path("", include("apps.processes.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
)
