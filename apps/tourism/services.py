from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from .models import (
    Destination,
    DestinationCategory,
    RecentlyViewedDestination,
    SavedPlace,
    Season,
    SEASON_MONTHS,
    Trip,
    TripDestination,
)

CATEGORY_TINTS = {
    "heritage-culture": "bg-gradient-to-br from-accent-500 to-accent-700",
    "nature-wildlife": "bg-gradient-to-br from-success/90 to-brand-900",
    "adventure-trekking": "bg-gradient-to-br from-brand-500 to-brand-800",
    "lakes-valleys": "bg-gradient-to-br from-brand-400 to-success",
    "spiritual-pilgrimage": "bg-gradient-to-br from-accent-400 to-brand-700",
}
DEFAULT_TINT = "bg-gradient-to-br from-brand-600 to-brand-800"


def get_category_tint(category_slug):
    return CATEGORY_TINTS.get(category_slug, DEFAULT_TINT)


def annotate_tints(destinations):
    destinations = list(destinations)
    for destination in destinations:
        destination.tint = get_category_tint(destination.category.slug)
    return destinations


def published_destinations_for_display():
    return (
        Destination.objects.filter(status=Destination.Status.PUBLISHED)
        .select_related("category")
        .annotate(highlight_count=Count("highlights", distinct=True))
    )


def get_categories_with_counts():
    categories = []
    for category in DestinationCategory.objects.all():
        count = Destination.objects.filter(status=Destination.Status.PUBLISHED, category=category).count()
        if not count:
            continue
        categories.append(
            {
                "category": category,
                "count": count,
                "url": f"{reverse('tourism:destination_list')}?category={category.slug}",
                "tint": get_category_tint(category.slug),
            }
        )
    return categories


def get_featured_destinations(limit=5):
    return annotate_tints(published_destinations_for_display().order_by("-last_verified_at", "title")[:limit])


def current_season():
    month = timezone.localdate().month
    for season, months in SEASON_MONTHS.items():
        if month in months:
            return season
    return None


def get_destinations_in_season():
    season = current_season()
    if not season:
        return []
    return annotate_tints(published_destinations_for_display().filter(best_season=season).order_by("title"))


def search_destinations(query="", category_slug=""):
    results = published_destinations_for_display()
    if category_slug:
        results = results.filter(category__slug=category_slug)
    if query:
        results = results.filter(title__icontains=query) | results.filter(region__icontains=query)
    return results.order_by("title")


def get_saved_destination_ids(user):
    if not user.is_authenticated:
        return set()
    return set(SavedPlace.objects.filter(user=user).values_list("destination_id", flat=True))


def toggle_saved_place(user, destination):
    saved = SavedPlace.objects.filter(user=user, destination=destination).first()
    if saved:
        saved.delete()
        return False
    SavedPlace.objects.create(user=user, destination=destination)
    return True


def record_destination_view(user, destination):
    viewed, created = RecentlyViewedDestination.objects.get_or_create(user=user, destination=destination)
    if not created:
        viewed.save(update_fields=["updated_at"])
    return viewed


def get_user_trips(user):
    return Trip.objects.filter(user=user).prefetch_related("stops__destination")


def create_trip(user, title, start_date=None, end_date=None, notes=""):
    return Trip.objects.create(user=user, title=title, start_date=start_date, end_date=end_date, notes=notes)


def get_trip_destination_ids(trip):
    return set(trip.stops.values_list("destination_id", flat=True))


def add_destination_to_trip(trip, destination, day_number=None):
    if trip.stops.filter(destination=destination).exists():
        return None
    next_order = trip.stops.count()
    return TripDestination.objects.create(
        trip=trip, destination=destination, order=next_order, day_number=day_number
    )


def remove_trip_destination(trip_destination):
    trip_destination.delete()
