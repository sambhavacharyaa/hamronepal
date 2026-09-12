from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Destination


class DestinationSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    i18n = True
    alternates = True
    x_default = True

    def items(self):
        return Destination.objects.filter(status=Destination.Status.PUBLISHED).order_by("slug")

    def lastmod(self, destination):
        return destination.updated_at

    def location(self, destination):
        return reverse("tourism:destination_detail", kwargs={"slug": destination.slug})
