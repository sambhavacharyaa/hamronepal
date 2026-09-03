from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import translate_url
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.dashboard import services as dashboard_services

from . import services
from .models import Process, ProcessCategory, ProcessVariant, UserProcessProgress
from .seo import build_faq_json_ld, build_howto_json_ld, to_json_ld_script

SEARCH_CONFIG_BY_LANGUAGE = {"en": "english", "ne": "simple"}


def search_view(request):
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()

    language = get_language()
    if language not in SEARCH_CONFIG_BY_LANGUAGE:
        language = "en"
    config = SEARCH_CONFIG_BY_LANGUAGE[language]
    vector_field = f"search_vector_{language}"

    results = services.published_processes_for_display()

    if category_slug:
        results = results.filter(category__slug=category_slug)

    if query:
        search_query = SearchQuery(query, config=config)
        results = (
            results.annotate(rank=SearchRank(F(vector_field), search_query))
            .filter(**{vector_field: search_query})
            .order_by("-rank")
        )
    else:
        results = results.order_by("title")

    context = {
        "query": query,
        "category_slug": category_slug,
        "results": results[:20],
        "saved_process_ids": dashboard_services.get_saved_process_ids(request.user),
    }
    template_name = "processes/partials/_search_results.html" if request.htmx else "processes/search_results.html"
    return render(request, template_name, context)


def process_list_view(request):
    category_slug = request.GET.get("category", "").strip()
    processes = services.published_processes_for_display().order_by("title")
    if category_slug:
        processes = processes.filter(category__slug=category_slug)

    categories = ProcessCategory.objects.filter(processes__status=Process.Status.PUBLISHED).distinct()

    return render(
        request,
        "processes/process_list.html",
        {
            "processes": processes,
            "categories": categories,
            "category_slug": category_slug,
            "saved_process_ids": dashboard_services.get_saved_process_ids(request.user),
        },
    )


def process_detail_view(request, slug):
    process = get_object_or_404(
        Process.objects.select_related("category", "responsible_organization"),
        slug=slug,
        status=Process.Status.PUBLISHED,
    )
    steps = list(process.steps.select_related("office").order_by("order"))
    requirements = list(process.requirements.order_by("order"))
    sources = list(process.sources.all())
    faqs = list(process.faqs.order_by("order"))
    has_variants = any(item.variant != ProcessVariant.ALL for item in steps + requirements)

    progress = None
    is_saved = False
    if request.user.is_authenticated:
        progress = UserProcessProgress.objects.filter(user=request.user, process=process).first()
        is_saved = process.id in dashboard_services.get_saved_process_ids(request.user)
        dashboard_services.record_process_view(request.user, process)

    howto_json_ld = to_json_ld_script(build_howto_json_ld(process, steps)) if steps else None
    faq_json_ld = to_json_ld_script(build_faq_json_ld(faqs)) if faqs else None

    hreflang_urls = {
        code: request.build_absolute_uri(translate_url(request.path, code))
        for code, _label in settings.LANGUAGES
    }

    return render(
        request,
        "processes/process_detail.html",
        {
            "process": process,
            "steps": steps,
            "requirements": requirements,
            "sources": sources,
            "faqs": faqs,
            "has_variants": has_variants,
            "progress": progress,
            "is_saved": is_saved,
            "howto_json_ld": howto_json_ld,
            "faq_json_ld": faq_json_ld,
            "hreflang_urls": hreflang_urls,
        },
    )


@login_required
@require_POST
def start_tracking_view(request, slug):
    process = get_object_or_404(Process, slug=slug, status=Process.Status.PUBLISHED)
    has_variants = process.steps.exclude(variant=ProcessVariant.ALL).exists() or process.requirements.exclude(
        variant=ProcessVariant.ALL
    ).exists()

    variant = request.POST.get("variant") or None
    if has_variants and variant not in (ProcessVariant.INDIVIDUAL, ProcessVariant.BUSINESS):
        messages.error(request, _("Please choose individual or business before starting."))
        return redirect("processes:process_detail", slug=slug)

    services.start_tracking(request.user, process, variant if has_variants else None)
    return redirect("processes:track_progress", slug=slug)


@login_required
def track_progress_view(request, slug):
    progress = get_object_or_404(
        UserProcessProgress.objects.select_related("process", "process_version"),
        user=request.user,
        process__slug=slug,
    )
    step_progress = progress.step_progress.select_related("step", "step__office").order_by("step__order")
    requirement_progress = progress.requirement_progress.select_related("requirement").order_by("requirement__order")
    percent = services.compute_percent(progress)

    return render(
        request,
        "processes/track_progress.html",
        {
            "progress": progress,
            "process": progress.process,
            "slug": slug,
            "step_progress": step_progress,
            "requirement_progress": requirement_progress,
            "percent": percent,
            "status_choices": UserProcessProgress.Status.choices,
        },
    )


@login_required
@require_POST
def toggle_step_view(request, slug, step_id):
    progress = get_object_or_404(UserProcessProgress, user=request.user, process__slug=slug)
    step_progress = get_object_or_404(progress.step_progress, step_id=step_id)
    step_progress = services.toggle_step_progress(progress, step_progress.step)
    return render(request, "processes/partials/_step_item.html", {"step_progress": step_progress, "slug": slug})


@login_required
@require_POST
def toggle_requirement_view(request, slug, requirement_id):
    progress = get_object_or_404(UserProcessProgress, user=request.user, process__slug=slug)
    requirement_progress = get_object_or_404(progress.requirement_progress, requirement_id=requirement_id)
    requirement_progress = services.toggle_requirement_progress(progress, requirement_progress.requirement)
    return render(
        request,
        "processes/partials/_requirement_item.html",
        {"requirement_progress": requirement_progress, "slug": slug},
    )


@login_required
@require_POST
def advance_status_view(request, slug):
    progress = get_object_or_404(UserProcessProgress, user=request.user, process__slug=slug)
    new_status = request.POST.get("status")
    if new_status in UserProcessProgress.Status.values:
        services.advance_status(progress, new_status)
        messages.success(request, _("Status updated."))
    return redirect("processes:track_progress", slug=slug)
