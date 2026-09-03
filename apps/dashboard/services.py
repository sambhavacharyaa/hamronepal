import math
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Profile
from apps.processes import services as process_services
from apps.processes.models import UserProcessProgress
from apps.tasks.models import Task

from .models import Notification, RecentlyViewedProcess, SavedProcess, UserDocument

REMINDER_THRESHOLDS_DAYS = [0, 1, 7, 30, 90]

DEADLINE_FILTERS = ("upcoming", "this_week", "this_month", "later", "overdue", "completed")


def get_saved_process_ids(user):
    if not user.is_authenticated:
        return set()
    return set(SavedProcess.objects.filter(user=user).values_list("process_id", flat=True))


def toggle_saved_process(user, process):
    saved = SavedProcess.objects.filter(user=user, process=process).first()
    if saved:
        saved.delete()
        return False
    SavedProcess.objects.create(user=user, process=process, version_at_save=process.current_version_number)
    return True


def record_process_view(user, process):
    viewed, created = RecentlyViewedProcess.objects.get_or_create(user=user, process=process)
    if not created:
        viewed.save(update_fields=["updated_at"])
    return viewed


def classify_urgency(days_until):
    if days_until < 0:
        return "overdue"
    if days_until <= 7:
        return "urgent"
    if days_until <= 30:
        return "soon"
    return "later"


def _describe_relative(days_until, present_verb, past_verb):
    if days_until < 0:
        days = abs(days_until)
        unit = "day" if days == 1 else "days"
        return f"{past_verb} {days} {unit} ago"
    if days_until == 0:
        return f"{present_verb} today"
    if days_until < 60:
        unit = "day" if days_until == 1 else "days"
        return f"{present_verb} in {days_until} {unit}"
    months = max(1, round(days_until / 30))
    unit = "month" if months == 1 else "months"
    return f"{present_verb} in {months} {unit}"


def describe_expiry(days_until):
    return _describe_relative(days_until, "expires", "expired")


def describe_due(days_until):
    return _describe_relative(days_until, "is due", "was due")


def _reminder_threshold_for(days_until):
    if days_until <= 0:
        return 0
    for threshold in REMINDER_THRESHOLDS_DAYS:
        if threshold > 0 and days_until <= threshold:
            return threshold
    return None


def get_deadlines(user, within_days=None, include_completed=False):
    today = timezone.localdate()
    deadlines = []

    task_qs = Task.objects.filter(user=user, due_date__isnull=False)
    if not include_completed:
        task_qs = task_qs.filter(is_completed=False)
    if within_days is not None:
        task_qs = task_qs.filter(due_date__lte=today + timedelta(days=within_days))
    for task in task_qs.order_by("due_date"):
        days_until = (task.due_date - today).days
        deadlines.append(
            {
                "kind": "task",
                "title": task.title,
                "date": task.due_date,
                "url": None,
                "days_until": days_until,
                "is_overdue": days_until < 0,
                "is_completed": task.is_completed,
                "completed_at": task.completed_at,
                "urgency": classify_urgency(days_until),
            }
        )

    document_qs = UserDocument.objects.filter(user=user, expiry_date__isnull=False).select_related("process")
    if within_days is not None:
        document_qs = document_qs.filter(expiry_date__lte=today + timedelta(days=within_days))
    for document in document_qs.order_by("expiry_date"):
        days_until = (document.expiry_date - today).days
        url = None
        if document.process:
            url = reverse("processes:process_detail", kwargs={"slug": document.process.slug})
        deadlines.append(
            {
                "kind": "document",
                "title": document.title,
                "date": document.expiry_date,
                "url": url,
                "days_until": days_until,
                "is_overdue": days_until < 0,
                "is_completed": False,
                "completed_at": None,
                "urgency": classify_urgency(days_until),
            }
        )

    deadlines.sort(key=lambda item: item["date"])
    return deadlines


def filter_deadlines(deadlines, bucket):
    if bucket == "overdue":
        return [d for d in deadlines if d["is_overdue"] and not d["is_completed"]]
    if bucket == "completed":
        items = [d for d in deadlines if d["is_completed"]]
        return sorted(items, key=lambda d: d["completed_at"] or d["date"], reverse=True)
    if bucket == "this_week":
        return [d for d in deadlines if not d["is_completed"] and 0 <= d["days_until"] <= 7]
    if bucket == "this_month":
        return [d for d in deadlines if not d["is_completed"] and 8 <= d["days_until"] <= 30]
    if bucket == "later":
        return [d for d in deadlines if not d["is_completed"] and d["days_until"] > 30]
    return [d for d in deadlines if not d["is_completed"] and not d["is_overdue"]]


RING_RADIUS = 28
RING_CIRCUMFERENCE = 2 * math.pi * RING_RADIUS


def compute_ring_dashoffset(percent):
    percent = max(0, min(100, percent))
    return round(RING_CIRCUMFERENCE * (1 - percent / 100), 2)


def compute_progress_counts(progress):
    total = progress.step_progress.count() + progress.requirement_progress.count()
    completed = (
        progress.step_progress.filter(is_completed=True).count()
        + progress.requirement_progress.filter(is_completed=True).count()
    )
    return completed, total


def sync_notifications(user):
    today = timezone.localdate()

    documents = UserDocument.objects.filter(user=user, expiry_date__isnull=False).select_related("process")
    for document in documents:
        days_until = (document.expiry_date - today).days
        threshold = _reminder_threshold_for(days_until)
        if threshold is None:
            continue
        level = Notification.Level.DANGER if days_until < 0 else (
            Notification.Level.WARNING if days_until <= 7 else Notification.Level.INFO
        )
        Notification.objects.get_or_create(
            user=user,
            dedupe_key=f"document_expiry_{document.id}_{threshold}",
            defaults={
                "category": Notification.Category.DOCUMENT_EXPIRY,
                "level": level,
                "message": f"Your {document.title} {describe_expiry(days_until)}.",
                "related_process": document.process,
                "related_document": document,
            },
        )

    tasks = Task.objects.filter(user=user, is_completed=False, due_date__isnull=False)
    for task in tasks:
        days_until = (task.due_date - today).days
        threshold = _reminder_threshold_for(days_until)
        if threshold is None:
            continue
        level = Notification.Level.DANGER if days_until < 0 else (
            Notification.Level.WARNING if days_until <= 7 else Notification.Level.INFO
        )
        Notification.objects.get_or_create(
            user=user,
            dedupe_key=f"task_due_{task.id}_{threshold}",
            defaults={
                "category": Notification.Category.TASK_DUE,
                "level": level,
                "message": f'Your task "{task.title}" {describe_due(days_until)}.',
                "related_task": task,
            },
        )

    stale_cutoff = timezone.now() - timedelta(days=14)
    stalled_progress = (
        UserProcessProgress.objects.filter(user=user, updated_at__lte=stale_cutoff)
        .exclude(status=UserProcessProgress.Status.COMPLETED)
        .select_related("process")
    )
    for progress in stalled_progress:
        Notification.objects.get_or_create(
            user=user,
            dedupe_key=f"stalled_process_{progress.id}",
            defaults={
                "category": Notification.Category.PROCESS_STALLED,
                "level": Notification.Level.INFO,
                "message": f"You haven't touched {progress.process.title} in a while.",
                "related_process": progress.process,
            },
        )

    active_progress = (
        UserProcessProgress.objects.filter(user=user)
        .exclude(status=UserProcessProgress.Status.COMPLETED)
        .select_related("process")
    )
    for progress in active_progress:
        completed, total = compute_progress_counts(progress)
        if not total:
            continue
        percent = int(completed / total * 100)
        milestone = next((candidate for candidate in (75, 50, 25) if percent >= candidate), None)
        if milestone is None:
            continue
        Notification.objects.get_or_create(
            user=user,
            dedupe_key=f"process_progress_{progress.id}_{milestone}",
            defaults={
                "category": Notification.Category.PROCESS_PROGRESS,
                "level": Notification.Level.INFO,
                "message": f"{progress.process.title}: {completed}/{total} steps completed.",
                "related_process": progress.process,
            },
        )

    saved_processes = SavedProcess.objects.filter(user=user).select_related("process")
    for saved in saved_processes:
        process = saved.process
        version = process.current_version_number
        if not version or version == saved.version_at_save:
            continue
        Notification.objects.get_or_create(
            user=user,
            dedupe_key=f"process_update_{process.id}_{version}",
            defaults={
                "category": Notification.Category.PROCESS_UPDATE,
                "level": Notification.Level.INFO,
                "message": f"{process.title} was updated. Review the latest steps and fees.",
                "related_process": process,
            },
        )


def dismiss_notification(notification):
    notification.is_dismissed = True
    notification.dismissed_at = timezone.now()
    notification.save(update_fields=["is_dismissed", "dismissed_at"])
    return notification


def mark_notification_read(notification):
    if notification.is_read:
        return notification
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=["is_read", "read_at"])
    return notification


def mark_all_notifications_read(user):
    return Notification.objects.filter(user=user, is_read=False, is_dismissed=False).update(
        is_read=True, read_at=timezone.now()
    )


def get_unread_notification_count(user):
    if not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, is_dismissed=False, is_read=False).count()


def get_notification_action_url(notification):
    category = notification.category
    if category == Notification.Category.TASK_DUE:
        return f"{reverse('core:dashboard')}#actions"
    if category in (Notification.Category.PROCESS_PROGRESS, Notification.Category.PROCESS_STALLED):
        if notification.related_process:
            return reverse("processes:track_progress", kwargs={"slug": notification.related_process.slug})
        return None
    if category in (Notification.Category.DOCUMENT_EXPIRY, Notification.Category.PROCESS_UPDATE):
        if notification.related_process:
            return reverse("processes:process_detail", kwargs={"slug": notification.related_process.slug})
        return None
    return None


def annotate_action_urls(notifications):
    for notification in notifications:
        notification.action_url = get_notification_action_url(notification)
    return notifications


def get_sidebar_context(user):
    profile, _created = Profile.objects.get_or_create(user=user)
    return {
        "profile": profile,
        "user_initial": (profile.display_name or user.email)[0].upper(),
        "notification_count": get_unread_notification_count(user),
    }


def get_recommended_processes(user, limit=3):
    tracked_ids = UserProcessProgress.objects.filter(user=user).values_list("process_id", flat=True)
    return list(
        process_services.published_processes_for_display().exclude(id__in=tracked_ids).order_by("title")[:limit]
    )


def get_dashboard_context(user):
    active_progress = (
        UserProcessProgress.objects.filter(user=user)
        .exclude(status=UserProcessProgress.Status.COMPLETED)
        .select_related("process")
        .order_by("-updated_at")
    )
    for progress in active_progress:
        progress.percent = process_services.compute_percent(progress)
        progress.completed_count, progress.total_count = compute_progress_counts(progress)

    completed_progress = (
        UserProcessProgress.objects.filter(user=user, status=UserProcessProgress.Status.COMPLETED)
        .select_related("process")
        .order_by("-completed_at")
    )

    tasks = Task.objects.filter(user=user).order_by("is_completed", "due_date")
    priority_tasks = tasks.filter(is_completed=False)

    documents = UserDocument.objects.filter(user=user).select_related("process")
    today = timezone.localdate()
    expiring_soon = today + timedelta(days=30)
    for document in documents:
        document.is_expiring_soon = bool(document.expiry_date and today <= document.expiry_date <= expiring_soon)
        document.is_expired = bool(document.expiry_date and document.expiry_date < today)

    saved_processes = SavedProcess.objects.filter(user=user).select_related("process", "process__category")
    recently_viewed = RecentlyViewedProcess.objects.filter(user=user).select_related(
        "process", "process__category"
    )[:6]

    deadlines_preview = get_deadlines(user, within_days=60)[:5]

    notifications_preview = list(
        Notification.objects.filter(user=user, is_dismissed=False)
        .select_related("related_process", "related_task", "related_document")[:3]
    )
    annotate_action_urls(notifications_preview)

    active_journey_count = len(active_progress)
    average_progress_percent = None
    if active_journey_count:
        average_progress_percent = round(sum(p.percent for p in active_progress) / active_journey_count)

    expiring_soon_count = sum(1 for d in documents if d.is_expiring_soon or d.is_expired)

    stats = {
        "active_journey_count": active_journey_count,
        "average_progress_percent": average_progress_percent,
        "ring_dashoffset": compute_ring_dashoffset(average_progress_percent or 0),
        "ring_circumference": round(RING_CIRCUMFERENCE, 2),
        "pending_task_count": priority_tasks.count(),
        "expiring_soon_count": expiring_soon_count,
        "completed_count": completed_progress.count(),
    }

    return {
        "active_progress": active_progress,
        "completed_progress": completed_progress,
        "tasks": tasks,
        "priority_tasks": priority_tasks,
        "documents": documents,
        "saved_processes": saved_processes,
        "recently_viewed": recently_viewed,
        "recommended_processes": get_recommended_processes(user),
        "deadlines_preview": deadlines_preview,
        "notifications_preview": notifications_preview,
        "stats": stats,
    }
