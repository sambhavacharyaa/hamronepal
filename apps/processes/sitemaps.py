from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Process


class ProcessSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Process.objects.filter(status=Process.Status.PUBLISHED).order_by("slug")

    def lastmod(self, process):
        return process.updated_at

    def location(self, process):
        return reverse("processes:process_detail", kwargs={"slug": process.slug})


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return ["core:home", "processes:process_list"]

    def location(self, name):
        return reverse(name)
