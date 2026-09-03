from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class ProcessVariant(models.TextChoices):
    ALL = "all", _("All")
    INDIVIDUAL = "individual", _("Individual")
    BUSINESS = "business", _("Business")


class ProcessCategory(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    icon = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "process categories"

    def __str__(self):
        return self.name


class Process(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        IN_REVIEW = "in_review", _("In Review")
        PUBLISHED = "published", _("Published")
        ARCHIVED = "archived", _("Archived")

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True)
    category = models.ForeignKey(ProcessCategory, on_delete=models.PROTECT, related_name="processes")
    summary = models.TextField(blank=True)
    description = models.TextField(blank=True)
    eligibility = models.TextField(blank=True)
    responsible_organization = models.ForeignKey(
        "organizations.GovernmentOrganization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="processes",
    )
    estimated_duration_min_days = models.PositiveIntegerField(null=True, blank=True)
    estimated_duration_max_days = models.PositiveIntegerField(null=True, blank=True)
    estimated_duration_note = models.CharField(max_length=255, blank=True)
    total_fee_note = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    last_verified_at = models.DateField(null=True, blank=True)
    last_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_processes",
    )
    current_version_number = models.CharField(max_length=20, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=255, blank=True)
    search_vector_en = SearchVectorField(null=True, editable=False)
    search_vector_ne = SearchVectorField(null=True, editable=False)

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "processes"
        indexes = [
            GinIndex(fields=["search_vector_en"]),
            GinIndex(fields=["search_vector_ne"]),
        ]

    def __str__(self):
        return self.title


class ProcessStep(TimeStampedModel):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    variant = models.CharField(max_length=20, choices=ProcessVariant.choices, default=ProcessVariant.ALL)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fee_note = models.CharField(max_length=255, blank=True)
    estimated_duration_note = models.CharField(max_length=255, blank=True)
    office = models.ForeignKey(
        "organizations.GovernmentOffice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="process_steps",
    )
    is_optional = models.BooleanField(default=False)

    class Meta:
        ordering = ["process", "order"]
        unique_together = ("process", "order")

    def __str__(self):
        return f"{self.process.title} — Step {self.order}: {self.title}"


class ProcessRequirement(TimeStampedModel):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="requirements")
    step = models.ForeignKey(
        ProcessStep,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requirements",
    )
    name = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)
    variant = models.CharField(max_length=20, choices=ProcessVariant.choices, default=ProcessVariant.ALL)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["process", "order"]

    def __str__(self):
        return self.name


class ProcessFAQ(TimeStampedModel):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["process", "order"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class ProcessSource(TimeStampedModel):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="sources")
    title = models.CharField(max_length=220)
    url = models.URLField()
    organization = models.ForeignKey(
        "organizations.GovernmentOrganization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="process_sources",
    )
    last_verified_date = models.DateField()
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_sources",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-last_verified_date"]

    def __str__(self):
        return self.title


class ProcessVersion(TimeStampedModel):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="versions")
    version_number = models.CharField(max_length=20)
    snapshot = models.JSONField()
    changelog = models.TextField(blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="published_process_versions",
    )
    published_at = models.DateTimeField()

    class Meta:
        ordering = ["-published_at"]
        unique_together = ("process", "version_number")

    def __str__(self):
        return f"{self.process.title} v{self.version_number}"


class UserProcessProgress(TimeStampedModel):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", _("Not Started")
        PREPARING = "preparing", _("Preparing")
        APPLIED = "applied", _("Applied")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="process_progress")
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="user_progress")
    process_version = models.ForeignKey(
        ProcessVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_progress",
    )
    variant_selected = models.CharField(max_length=20, choices=ProcessVariant.choices, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "process")
        verbose_name_plural = "user process progress"

    def __str__(self):
        return f"{self.user} — {self.process.title} ({self.status})"


class UserStepProgress(TimeStampedModel):
    progress = models.ForeignKey(UserProcessProgress, on_delete=models.CASCADE, related_name="step_progress")
    step = models.ForeignKey(ProcessStep, on_delete=models.CASCADE, related_name="user_progress")
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("progress", "step")
        verbose_name_plural = "user step progress"

    def __str__(self):
        return f"{self.progress} — {self.step.title}"


class UserRequirementProgress(TimeStampedModel):
    progress = models.ForeignKey(UserProcessProgress, on_delete=models.CASCADE, related_name="requirement_progress")
    requirement = models.ForeignKey(ProcessRequirement, on_delete=models.CASCADE, related_name="user_progress")
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("progress", "requirement")
        verbose_name_plural = "user requirement progress"

    def __str__(self):
        return f"{self.progress} — {self.requirement.name}"


class ProcessExperience(TimeStampedModel):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="experiences")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="process_experiences")
    body = models.TextField()
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} on {self.process}"
