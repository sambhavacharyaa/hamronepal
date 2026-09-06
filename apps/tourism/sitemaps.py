from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Destination


class DestinationSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Destination.objects.filter(status=Destination.Status.PUBLISHED).order_by("slug")

    def lastmod(self, destination):
        return destination.updated_at

    def location(self, destination):
        return reverse("tourism:destination_detail", kwargs={"slug": destination.slug})
