from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from . import services
from .forms import TaskForm
from .models import Task


@login_required
@require_POST
def task_create_view(request):
    form = TaskForm(request.POST)
    if form.is_valid():
        task = form.save(commit=False)
        task.user = request.user
        task.save()
        messages.success(request, _("Task added."))
    else:
        messages.error(request, _("Could not add task. Please check the form."))
    return redirect("core:dashboard")


@login_required
@require_POST
def task_toggle_view(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task = services.toggle_completed(task)
    return render(request, "tasks/partials/_task_item.html", {"task": task})


@login_required
@require_POST
def task_delete_view(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.delete()
    return HttpResponse("")
