from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_image_file_size

private_document_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def document_upload_path(instance, filename):
    return f"documents/{instance.user_id}/{filename}"


class SavedProcess(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_processes")
    process = models.ForeignKey("processes.Process", on_delete=models.CASCADE, related_name="saved_by")
    version_at_save = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ("user", "process")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} saved {self.process}"


class RecentlyViewedProcess(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recently_viewed")
    process = models.ForeignKey("processes.Process", on_delete=models.CASCADE, related_name="recently_viewed_by")

    class Meta:
        unique_together = ("user", "process")
        ordering = ["-updated_at"]
        verbose_name_plural = "recently viewed processes"

    def __str__(self):
        return f"{self.user} viewed {self.process}"


class UserDocument(TimeStampedModel):
    class DocumentType(models.TextChoices):
        CITIZENSHIP = "citizenship", _("Citizenship certificate")
        PASSPORT = "passport", _("Passport")
        DRIVING_LICENSE = "driving_license", _("Driving license")
        PAN_CARD = "pan_card", _("PAN card")
        OTHER = "other", _("Other")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    process = models.ForeignKey(
        "processes.Process", null=True, blank=True, on_delete=models.SET_NULL, related_name="documents"
    )
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER)
    title = models.CharField(max_length=220)
    image = models.ImageField(
        upload_to=document_upload_path,
        storage=private_document_storage,
        blank=True,
        validators=[validate_image_file_size],
    )
    issued_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["expiry_date"]

    def __str__(self):
        return self.title


class Notification(TimeStampedModel):
    class Level(models.TextChoices):
        INFO = "info", _("Info")
        WARNING = "warning", _("Warning")
        DANGER = "danger", _("Danger")

    class Category(models.TextChoices):
        DOCUMENT_EXPIRY = "document_expiry", _("Document expiry")
        TASK_DUE = "task_due", _("Task due")
        PROCESS_PROGRESS = "process_progress", _("Process progress")
        PROCESS_STALLED = "process_stalled", _("Process stalled")
        PROCESS_UPDATE = "process_update", _("Process update")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.PROCESS_UPDATE)
    message = models.CharField(max_length=255)
    related_process = models.ForeignKey(
        "processes.Process", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    related_task = models.ForeignKey(
        "tasks.Task", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    related_document = models.ForeignKey(
        UserDocument, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    dedupe_key = models.CharField(max_length=100)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    push_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "dedupe_key")
        ordering = ["-created_at"]

    def __str__(self):
        return self.message
