from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_image_file_size


class DestinationCategory(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    icon = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, validators=[validate_image_file_size])
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "destination categories"

    def __str__(self):
        return self.name


class Season(models.TextChoices):
    AUTUMN = "autumn", _("Autumn (Sep-Nov)")
    WINTER = "winter", _("Winter (Dec-Feb)")
    SPRING = "spring", _("Spring (Mar-May)")
    MONSOON = "monsoon", _("Monsoon (Jun-Aug)")


SEASON_MONTHS = {
    Season.AUTUMN: (9, 10, 11),
    Season.WINTER: (12, 1, 2),
    Season.SPRING: (3, 4, 5),
    Season.MONSOON: (6, 7, 8),
}


class Destination(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True)
    category = models.ForeignKey(DestinationCategory, on_delete=models.PROTECT, related_name="destinations")
    region = models.CharField(max_length=120)
    summary = models.TextField(blank=True)
    description = models.TextField(blank=True)
    highlights_intro = models.CharField(max_length=255, blank=True)
    best_season = models.CharField(max_length=20, choices=Season.choices, blank=True)
    budget_note = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="destinations/", blank=True, validators=[validate_image_file_size])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    source_url = models.URLField(blank=True)
    source_note = models.CharField(max_length=255, blank=True)
    last_verified_at = models.DateField(null=True, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=255, blank=True)
    related_processes = models.ManyToManyField(
        "processes.Process", blank=True, related_name="tourism_destinations"
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class DestinationHighlight(TimeStampedModel):
    class Kind(models.TextChoices):
        ACTIVITY = "activity", _("Thing to do")
        FOOD = "food", _("Food & experience")
        STAY = "stay", _("Where to stay")
        TRANSPORT = "transport", _("Getting around")

    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="highlights")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.ACTIVITY)
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["destination", "kind", "order"]

    def __str__(self):
        return self.title


class SavedPlace(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_places")
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="saved_by")

    class Meta:
        unique_together = ("user", "destination")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} saved {self.destination}"


class RecentlyViewedDestination(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recently_viewed_destinations")
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="recently_viewed_by")

    class Meta:
        unique_together = ("user", "destination")
        ordering = ["-updated_at"]
        verbose_name_plural = "recently viewed destinations"

    def __str__(self):
        return f"{self.user} viewed {self.destination}"


class Trip(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trips")
    title = models.CharField(max_length=220)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class TripDestination(TimeStampedModel):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="stops")
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="trip_stops")
    order = models.PositiveIntegerField(default=0)
    day_number = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["trip", "order"]

    def __str__(self):
        return f"{self.destination} in {self.trip}"
