from urllib.parse import quote

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models import Count, Min, Prefetch
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    Process,
    ProcessCategory,
    ProcessExperience,
    ProcessSource,
    ProcessVariant,
    UserProcessProgress,
    UserRequirementProgress,
    UserStepProgress,
)


class PublishError(Exception):
    pass


def _update_search_vectors(process):
    Process.objects.filter(pk=process.pk).update(
        search_vector_en=(
            SearchVector("title_en", weight="A", config="english")
            + SearchVector("summary_en", weight="B", config="english")
            + SearchVector("description_en", weight="C", config="english")
        ),
        search_vector_ne=(
            SearchVector("title_ne", weight="A", config="simple")
            + SearchVector("summary_ne", weight="B", config="simple")
            + SearchVector("description_ne", weight="C", config="simple")
        ),
    )


def _serialize_process(process):
    return {
        "title": process.title,
        "slug": process.slug,
        "summary": process.summary,
        "description": process.description,
        "eligibility": process.eligibility,
        "status": process.status,
        "steps": [
            {
                "order": step.order,
                "title": step.title,
                "description": step.description,
                "variant": step.variant,
                "fee_amount": str(step.fee_amount) if step.fee_amount is not None else None,
                "fee_note": step.fee_note,
                "estimated_duration_note": step.estimated_duration_note,
                "is_optional": step.is_optional,
            }
            for step in process.steps.order_by("order")
        ],
        "requirements": [
            {
                "name": requirement.name,
                "description": requirement.description,
                "is_mandatory": requirement.is_mandatory,
                "variant": requirement.variant,
                "order": requirement.order,
            }
            for requirement in process.requirements.order_by("order")
        ],
        "sources": [
            {
                "title": source.title,
                "url": source.url,
                "last_verified_date": source.last_verified_date.isoformat(),
            }
            for source in process.sources.all()
        ],
        "faqs": [
            {
                "question": faq.question,
                "answer": faq.answer,
                "order": faq.order,
            }
            for faq in process.faqs.order_by("order")
        ],
    }


def publish_new_version(process, user, changelog=""):
    if not process.sources.exists():
        raise PublishError("cannot publish: process has no cited sources")

    next_number = str(process.versions.count() + 1)
    now = timezone.now()

    version = process.versions.create(
        version_number=next_number,
        snapshot=_serialize_process(process),
        changelog=changelog,
        published_by=user,
        published_at=now,
    )

    process.status = Process.Status.PUBLISHED
    process.current_version_number = next_number
    process.last_verified_at = now.date()
    process.last_verified_by = user
    process.save(
        update_fields=[
            "status",
            "current_version_number",
            "last_verified_at",
            "last_verified_by",
            "updated_at",
        ]
    )
    _update_search_vectors(process)

    return version


def start_tracking(user, process, variant=None):
    progress, created = UserProcessProgress.objects.get_or_create(
        user=user,
        process=process,
        defaults={
            "process_version": process.versions.order_by("-published_at").first(),
            "variant_selected": variant,
            "started_at": timezone.now(),
        },
    )
    if not created:
        return progress

    steps = process.steps.all()
    requirements = process.requirements.all()
    if variant:
        steps = steps.filter(variant__in=[ProcessVariant.ALL, variant])
        requirements = requirements.filter(variant__in=[ProcessVariant.ALL, variant])

    UserStepProgress.objects.bulk_create(
        UserStepProgress(progress=progress, step=step) for step in steps
    )
    UserRequirementProgress.objects.bulk_create(
        UserRequirementProgress(progress=progress, requirement=requirement) for requirement in requirements
    )

    return progress


def _mark_preparing_on_first_progress(progress):
    if progress.status == UserProcessProgress.Status.NOT_STARTED:
        progress.status = UserProcessProgress.Status.PREPARING
        progress.save(update_fields=["status", "updated_at"])


def toggle_step_progress(progress, step):
    step_progress = progress.step_progress.get(step=step)
    step_progress.is_completed = not step_progress.is_completed
    step_progress.completed_at = timezone.now() if step_progress.is_completed else None
    step_progress.save(update_fields=["is_completed", "completed_at", "updated_at"])
    if step_progress.is_completed:
        _mark_preparing_on_first_progress(progress)
    return step_progress


def toggle_requirement_progress(progress, requirement):
    requirement_progress = progress.requirement_progress.get(requirement=requirement)
    requirement_progress.is_completed = not requirement_progress.is_completed
    requirement_progress.completed_at = timezone.now() if requirement_progress.is_completed else None
    requirement_progress.save(update_fields=["is_completed", "completed_at", "updated_at"])
    if requirement_progress.is_completed:
        _mark_preparing_on_first_progress(progress)
    return requirement_progress


def advance_status(progress, new_status):
    if new_status not in UserProcessProgress.Status.values:
        raise ValueError(f"unknown status: {new_status}")

    progress.status = new_status
    if new_status == UserProcessProgress.Status.COMPLETED and progress.completed_at is None:
        progress.completed_at = timezone.now()
    progress.save(update_fields=["status", "completed_at", "updated_at"])
    return progress


def compute_percent(progress):
    total = progress.step_progress.count() + progress.requirement_progress.count()
    if not total:
        return 0
    completed = (
        progress.step_progress.filter(is_completed=True).count()
        + progress.requirement_progress.filter(is_completed=True).count()
    )
    return int(completed / total * 100)


def get_resume_progress(user):
    if not user.is_authenticated:
        return None
    active = (
        UserProcessProgress.objects.filter(user=user)
        .exclude(status=UserProcessProgress.Status.COMPLETED)
        .select_related("process")
    )
    best = None
    best_percent = -1
    for progress in active:
        percent = compute_percent(progress)
        if percent > best_percent or (best is not None and percent == best_percent and progress.updated_at > best.updated_at):
            best = progress
            best_percent = percent
    if best is not None:
        best.percent = best_percent
    return best


def get_product_experience_demo():
    process = (
        Process.objects.filter(status=Process.Status.PUBLISHED, slug="register-for-a-pan")
        .prefetch_related("requirements", "steps", "sources")
        .first()
    )
    if process is None:
        return None
    requirements = list(process.requirements.order_by("order"))
    steps = list(process.steps.order_by("order"))
    source = process.sources.order_by("-last_verified_date").first()
    for index, requirement in enumerate(requirements):
        requirement.demo_done = index < 2
    for index, step in enumerate(steps):
        step.demo_done = index < 1
    total = len(requirements) + len(steps)
    done = sum(1 for r in requirements if r.demo_done) + sum(1 for s in steps if s.demo_done)
    return {
        "process": process,
        "requirements": requirements,
        "steps": steps,
        "percent": int(done / total * 100) if total else 0,
        "next_step": next((s for s in steps if not s.demo_done), None),
        "source": source,
    }


def get_homepage_experiences(limit=6):
    return list(
        ProcessExperience.objects.filter(is_published=True)
        .select_related("process", "user")
        .order_by("-created_at")[:limit]
    )


def get_oldest_verification_days():
    oldest_date = ProcessSource.objects.filter(process__status=Process.Status.PUBLISHED).aggregate(
        Min("last_verified_date")
    )["last_verified_date__min"]
    if oldest_date is None:
        return None
    return (timezone.localdate() - oldest_date).days


CATEGORY_ICONS = {
    "business": {"icon": "briefcase", "color": "primary"},
    "travel-documents": {"icon": "airplane-takeoff", "color": "accent"},
}


def get_homepage_categories():
    categories = []
    for category in ProcessCategory.objects.all():
        meta = CATEGORY_ICONS.get(category.slug, {"icon": "file-text", "color": "primary"})
        categories.append(
            {
                "name": category.name,
                "count": Process.objects.filter(status=Process.Status.PUBLISHED, category=category).count(),
                "url": f"{reverse('processes:process_list')}?category={category.slug}",
                "icon": meta["icon"],
                "badge_class": ICON_BADGE_CLASSES[meta["color"]],
            }
        )
    return categories


def published_processes_for_display():
    return (
        Process.objects.filter(status=Process.Status.PUBLISHED)
        .select_related("category")
        .annotate(
            step_count=Count("steps", distinct=True),
            requirement_count=Count("requirements", distinct=True),
        )
        .prefetch_related(
            Prefetch(
                "sources",
                queryset=ProcessSource.objects.order_by("-last_verified_date"),
                to_attr="prefetched_sources",
            )
        )
    )


ICON_BADGE_CLASSES = {
    "primary": "bg-primary/10 text-primary",
    "accent": "bg-accent/10 text-accent",
    "success": "bg-success/10 text-success",
    "warning": "bg-warning/10 text-warning",
}

HOMEPAGE_SITUATIONS = [
    {"label": _("I'm starting a business"), "category_slug": "business", "icon": "briefcase", "color": "primary"},
    {"label": _("I'm going abroad"), "category_slug": "travel-documents", "icon": "airplane-takeoff", "color": "accent"},
    {"label": _("I need a tax ID"), "query": "PAN", "icon": "identification-card", "color": "success"},
    {"label": _("I'm renewing my driving license"), "query": "driving license", "icon": "steering-wheel", "color": "warning"},
    {"label": _("I'm buying a vehicle"), "query": "vehicle", "icon": "car", "color": "primary"},
    {"label": _("I'm renting a house"), "query": "rent", "icon": "house-line", "color": "accent"},
]


def get_homepage_situations():
    published = Process.objects.filter(status=Process.Status.PUBLISHED)
    situations = []
    for situation in HOMEPAGE_SITUATIONS:
        if "category_slug" in situation:
            count = published.filter(category__slug=situation["category_slug"]).count()
            url = f"{reverse('processes:process_list')}?category={situation['category_slug']}"
        else:
            search_query = SearchQuery(situation["query"], config="english")
            count = published.filter(search_vector_en=search_query).count()
            url = f"{reverse('processes:search')}?q={quote(situation['query'])}"
        situations.append(
            {
                "label": situation["label"],
                "count": count,
                "url": url,
                "icon": situation["icon"],
                "badge_class": ICON_BADGE_CLASSES[situation["color"]],
            }
        )
    return situations
