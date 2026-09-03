from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Task(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    related_process_progress = models.ForeignKey(
        "processes.UserProcessProgress",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    related_step = models.ForeignKey(
        "processes.ProcessStep",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )

    class Meta:
        ordering = ["due_date", "title"]

    def __str__(self):
        return self.title
