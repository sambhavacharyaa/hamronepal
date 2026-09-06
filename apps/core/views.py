from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.dashboard import services as dashboard_services
from apps.dashboard.forms import UserDocumentForm
from apps.locations import services as location_services
from apps.processes import services as process_services
from apps.processes.seo import build_website_json_ld, to_json_ld_script
from apps.tasks.forms import TaskForm


def home_view(request):
    situations = process_services.get_homepage_situations()
    catalog = process_services.published_processes_for_display().order_by("title")
    website_json_ld = build_website_json_ld(
        request.build_absolute_uri(reverse("core:home")),
        request.build_absolute_uri(reverse("processes:search")),
    )
    return render(
        request,
        "core/home.html",
        {
            "situations": situations,
            "results": catalog,
            "published_count": catalog.count(),
            "oldest_verification_days": process_services.get_oldest_verification_days(),
            "resume_progress": process_services.get_resume_progress(request.user),
            "website_json_ld": to_json_ld_script(website_json_ld),
            "experiences": process_services.get_homepage_experiences(),
            "product_experience": process_services.get_product_experience_demo(),
            "location_sample": location_services.get_homepage_location_sample(),
            "categories": process_services.get_homepage_categories(),
            "saved_process_ids": dashboard_services.get_saved_process_ids(request.user),
        },
    )


@require_GET
def robots_txt_view(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /dashboard/",
        "Disallow: /tourism/trips/",
        "Disallow: /tourism/saved/",
        "",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@login_required
def dashboard_view(request):
    dashboard_services.sync_notifications(request.user)
    context = dashboard_services.get_dashboard_context(request.user)
    context.update(
        {
            "task_form": TaskForm(),
            "document_form": UserDocumentForm(prefix="document"),
            "saved_process_ids": dashboard_services.get_saved_process_ids(request.user),
        }
    )
    context.update(dashboard_services.get_sidebar_context(request.user))
    return render(request, "core/dashboard.html", context)
