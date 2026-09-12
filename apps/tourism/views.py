from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.core.seo import build_breadcrumb_json_ld, to_json_ld_script
from apps.processes.models import Process

from . import services
from .forms import TripForm
from .models import Destination, DestinationCategory, Trip, TripDestination
from .seo import build_tourist_destination_json_ld


def tourism_home_view(request):
    context = {
        "categories": services.get_categories_with_counts(),
        "featured_destinations": services.get_featured_destinations(),
        "seasonal_destinations": services.get_destinations_in_season(),
        "current_season": services.current_season(),
        "saved_destination_ids": services.get_saved_destination_ids(request.user),
        "page_title": _("Explore Nepal"),
        "meta_description": _(
            "Discover Nepal, plan your route, and organize your trip in one place, "
            "from heritage cities to Himalayan trails."
        ),
    }
    if request.user.is_authenticated:
        context["user_trips"] = list(services.get_user_trips(request.user)[:3])
    return render(request, "tourism/home.html", context)


def destination_list_view(request):
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    results = services.annotate_tints(services.search_destinations(query, category_slug))
    return render(
        request,
        "tourism/destination_list.html",
        {
            "query": query,
            "category_slug": category_slug,
            "categories": DestinationCategory.objects.all(),
            "results": results,
            "saved_destination_ids": services.get_saved_destination_ids(request.user),
            "page_title": _("Nepal travel destinations"),
            "meta_description": _(
                "Real, verified travel destinations across Nepal, from heritage cities to "
                "national parks and Himalayan trekking regions."
            ),
            "noindex": bool(query),
        },
    )


def destination_detail_view(request, slug):
    destination = get_object_or_404(
        Destination.objects.select_related("category").prefetch_related("highlights", "related_processes"),
        slug=slug,
        status=Destination.Status.PUBLISHED,
    )
    highlights = list(destination.highlights.order_by("kind", "order"))
    related_processes = list(destination.related_processes.filter(status=Process.Status.PUBLISHED))

    is_saved = False
    user_trips = []
    if request.user.is_authenticated:
        is_saved = destination.id in services.get_saved_destination_ids(request.user)
        services.record_destination_view(request.user, destination)
        user_trips = list(services.get_user_trips(request.user))

    image_url = request.build_absolute_uri(destination.image.url) if destination.image else None
    destination_json_ld = to_json_ld_script(build_tourist_destination_json_ld(destination, image_url=image_url))
    breadcrumb_json_ld = to_json_ld_script(
        build_breadcrumb_json_ld(
            [
                (_("Home"), request.build_absolute_uri(reverse("core:home"))),
                (_("Explore Nepal"), request.build_absolute_uri(reverse("tourism:home"))),
                (destination.title, request.build_absolute_uri(request.path)),
            ]
        )
    )

    return render(
        request,
        "tourism/destination_detail.html",
        {
            "destination": destination,
            "highlights": highlights,
            "related_processes": related_processes,
            "is_saved": is_saved,
            "user_trips": user_trips,
            "destination_json_ld": destination_json_ld,
            "breadcrumb_json_ld": breadcrumb_json_ld,
            "tint": services.get_category_tint(destination.category.slug),
            "page_title": destination.meta_title or destination.title,
            "meta_description": destination.meta_description or destination.summary,
            "og_image": image_url,
        },
    )


@login_required
@require_POST
def toggle_saved_view(request, slug):
    destination = get_object_or_404(Destination, slug=slug, status=Destination.Status.PUBLISHED)
    is_saved = services.toggle_saved_place(request.user, destination)
    return render(
        request,
        "components/tourism/save_button.html",
        {"destination": destination, "is_saved": is_saved},
    )


@login_required
def saved_places_view(request):
    saved = list(
        request.user.saved_places.select_related("destination", "destination__category").order_by("-created_at")
    )
    for item in saved:
        item.destination.tint = services.get_category_tint(item.destination.category.slug)
    return render(request, "tourism/saved_places.html", {"saved_places": saved})


@login_required
def trip_list_view(request):
    trips = services.get_user_trips(request.user)
    return render(request, "tourism/trip_list.html", {"trips": trips, "trip_form": TripForm()})


@login_required
@require_POST
def trip_create_view(request):
    form = TripForm(request.POST)
    if form.is_valid():
        trip = form.save(commit=False)
        trip.user = request.user
        trip.save()
        messages.success(request, _("Trip created."))
        return redirect("tourism:trip_detail", pk=trip.pk)
    messages.error(request, _("Could not create trip. Please check the form."))
    return redirect("tourism:trip_list")


@login_required
def trip_detail_view(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    stops = trip.stops.select_related("destination", "destination__category").order_by("order")
    trip_destination_ids = services.get_trip_destination_ids(trip)
    return render(
        request,
        "tourism/trip_detail.html",
        {
            "trip": trip,
            "stops": stops,
            "trip_destination_ids": trip_destination_ids,
            "available_destinations": services.published_destinations_for_display().exclude(
                id__in=trip_destination_ids
            ),
        },
    )


@login_required
@require_POST
def trip_delete_view(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    trip.delete()
    messages.success(request, _("Trip deleted."))
    return redirect("tourism:trip_list")


def _render_trip_itinerary_section(request, trip):
    stops = trip.stops.select_related("destination", "destination__category").order_by("order")
    trip_destination_ids = services.get_trip_destination_ids(trip)
    available_destinations = services.published_destinations_for_display().exclude(id__in=trip_destination_ids)
    return render(
        request,
        "components/tourism/trip_itinerary_section.html",
        {"trip": trip, "stops": stops, "available_destinations": available_destinations},
    )


@login_required
@require_POST
def trip_add_destination_view(request, pk, destination_slug):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    destination = get_object_or_404(Destination, slug=destination_slug, status=Destination.Status.PUBLISHED)
    services.add_destination_to_trip(trip, destination)
    return _render_trip_itinerary_section(request, trip)


@login_required
@require_POST
def trip_remove_destination_view(request, trip_pk, pk):
    trip = get_object_or_404(Trip, pk=trip_pk, user=request.user)
    stop = get_object_or_404(TripDestination, pk=pk, trip=trip)
    services.remove_trip_destination(stop)
    return _render_trip_itinerary_section(request, trip)
