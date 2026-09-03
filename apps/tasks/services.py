from django.utils import timezone


def toggle_completed(task):
    task.is_completed = not task.is_completed
    task.completed_at = timezone.now() if task.is_completed else None
    task.save(update_fields=["is_completed", "completed_at", "updated_at"])
    return task
