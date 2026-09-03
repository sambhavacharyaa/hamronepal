from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from apps.processes.models import Process

from . import services
from .forms import UserDocumentForm
from .models import Notification, UserDocument


@login_required
@require_POST
def document_create_view(request):
    form = UserDocumentForm(request.POST, request.FILES, prefix="document")
    if form.is_valid():
        document = form.save(commit=False)
        document.user = request.user
        document.save()
        messages.success(request, _("Document added."))
    else:
        messages.error(request, _("Could not add document. Please check the form."))
    return HttpResponseRedirect(f"{reverse('core:dashboard')}#documents")


@login_required
@require_POST
def document_delete_view(request, pk):
    document = get_object_or_404(UserDocument, pk=pk, user=request.user)
    document.delete()
    return HttpResponse("")


@login_required
@require_GET
def document_file_view(request, pk):
    document = get_object_or_404(UserDocument, pk=pk, user=request.user)
    if not document.image:
        raise Http404()
    filename = document.image.name.rsplit("/", 1)[-1]
    return FileResponse(document.image.open("rb"), filename=filename)


@login_required
@require_POST
def toggle_saved_view(request, slug):
    process = get_object_or_404(Process, slug=slug, status=Process.Status.PUBLISHED)
    is_saved = services.toggle_saved_process(request.user, process)
    return render(
        request,
        "components/dashboard/save_button.html",
        {"process": process, "is_saved": is_saved},
    )


DEADLINE_FILTER_LABELS = {
    "upcoming": _("Upcoming"),
    "this_week": _("This week"),
    "this_month": _("This month"),
    "later": _("Later"),
    "overdue": _("Overdue"),
    "completed": _("Completed"),
}


@login_required
def deadlines_view(request):
    services.sync_notifications(request.user)
    bucket = request.GET.get("filter", "upcoming")
    if bucket not in services.DEADLINE_FILTERS:
        bucket = "upcoming"
    deadlines = services.get_deadlines(request.user, within_days=None, include_completed=True)
    base_url = reverse("dashboard:deadlines")
    filter_tabs = [
        {"key": key, "label": DEADLINE_FILTER_LABELS[key], "url": f"{base_url}?filter={key}"}
        for key in services.DEADLINE_FILTERS
    ]
    context = {
        "active_filter": bucket,
        "filter_tabs": filter_tabs,
        "deadlines": services.filter_deadlines(deadlines, bucket),
    }
    context.update(services.get_sidebar_context(request.user))
    return render(request, "dashboard/deadlines.html", context)


@login_required
def notifications_view(request):
    services.sync_notifications(request.user)
    notifications = list(
        Notification.objects.filter(user=request.user, is_dismissed=False)
        .select_related("related_process", "related_task", "related_document")
    )
    services.annotate_action_urls(notifications)
    context = {
        "notifications": notifications,
        "has_unread": any(not notification.is_read for notification in notifications),
    }
    context.update(services.get_sidebar_context(request.user))
    return render(request, "dashboard/notifications.html", context)


def _notification_badge_oob(request):
    count = services.get_unread_notification_count(request.user)
    sidebar_badge = render_to_string(
        "components/dashboard/notification_badge.html",
        {
            "badge_id": "sidebar-notification-badge",
            "notification_count": count,
            "position_class": "right-3 top-2.5",
            "extra_class": "lg:[aside[data-collapsed=true]_&]:right-1.5 lg:[aside[data-collapsed=true]_&]:top-1.5",
            "oob": True,
        },
    )
    navbar_badge = render_to_string(
        "components/dashboard/notification_badge.html",
        {
            "badge_id": "navbar-notification-badge",
            "notification_count": count,
            "position_class": "right-0.5 top-0.5",
            "oob": True,
        },
    )
    return sidebar_badge + navbar_badge


@login_required
@require_POST
def dismiss_notification_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    services.dismiss_notification(notification)
    return HttpResponse(_notification_badge_oob(request))


@login_required
@require_POST
def mark_notification_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    services.mark_notification_read(notification)
    notification.action_url = services.get_notification_action_url(notification)
    item_html = render_to_string(
        "components/dashboard/notification_item.html", {"notification": notification}, request=request
    )
    return HttpResponse(item_html + _notification_badge_oob(request))


@login_required
@require_POST
def mark_all_notifications_read_view(request):
    services.mark_all_notifications_read(request.user)
    return HttpResponseRedirect(reverse("dashboard:notifications"))
