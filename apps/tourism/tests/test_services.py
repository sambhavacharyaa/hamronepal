from unittest.mock import patch

from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.tourism import services
from apps.tourism.models import Destination, Season, TripDestination

from .factories import DestinationCategoryFactory, DestinationFactory


class SearchDestinationsTests(TestCase):
    def setUp(self):
        self.heritage = DestinationCategoryFactory(name="Heritage & Culture", slug="heritage-culture")
        self.nature = DestinationCategoryFactory(name="Nature & Wildlife", slug="nature-wildlife")
        self.kathmandu = DestinationFactory(title="Kathmandu Valley", region="Kathmandu Valley", category=self.heritage)
        self.chitwan = DestinationFactory(title="Chitwan National Park", region="Chitwan, Terai", category=self.nature)
        self.draft = DestinationFactory(title="Draft Place", status=Destination.Status.DRAFT)

    def test_only_published_destinations_are_returned(self):
        results = services.search_destinations()
        self.assertNotIn(self.draft, list(results))

    def test_query_matches_title(self):
        results = services.search_destinations(query="kathmandu")
        self.assertEqual(list(results), [self.kathmandu])

    def test_query_matches_region(self):
        results = services.search_destinations(query="terai")
        self.assertEqual(list(results), [self.chitwan])

    def test_category_filter(self):
        results = services.search_destinations(category_slug="nature-wildlife")
        self.assertEqual(list(results), [self.chitwan])


class SavedPlaceServiceTests(TestCase):
    def test_toggle_saves_then_unsaves(self):
        user = UserFactory()
        destination = DestinationFactory()

        first_toggle = services.toggle_saved_place(user, destination)
        second_toggle = services.toggle_saved_place(user, destination)

        self.assertTrue(first_toggle)
        self.assertFalse(second_toggle)

    def test_get_saved_destination_ids_empty_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(services.get_saved_destination_ids(AnonymousUser()), set())


class SeasonServiceTests(TestCase):
    def test_get_destinations_in_season_filters_by_current_season(self):
        autumn_destination = DestinationFactory(title="Autumn pick", best_season=Season.AUTUMN)
        DestinationFactory(title="Winter pick", best_season=Season.WINTER)

        with patch("apps.tourism.services.current_season", return_value=Season.AUTUMN):
            results = services.get_destinations_in_season()

        self.assertEqual([d.title for d in results], ["Autumn pick"])

    def test_no_current_season_returns_empty(self):
        DestinationFactory(best_season=Season.AUTUMN)

        with patch("apps.tourism.services.current_season", return_value=None):
            results = services.get_destinations_in_season()

        self.assertEqual(results, [])


class TripServiceTests(TestCase):
    def test_add_destination_to_trip(self):
        user = UserFactory()
        trip = services.create_trip(user, title="A trip")
        destination = DestinationFactory()

        stop = services.add_destination_to_trip(trip, destination)

        self.assertIsNotNone(stop)
        self.assertEqual(trip.stops.count(), 1)

    def test_adding_same_destination_twice_does_not_duplicate(self):
        user = UserFactory()
        trip = services.create_trip(user, title="A trip")
        destination = DestinationFactory()

        services.add_destination_to_trip(trip, destination)
        second_attempt = services.add_destination_to_trip(trip, destination)

        self.assertIsNone(second_attempt)
        self.assertEqual(trip.stops.count(), 1)

    def test_remove_trip_destination(self):
        user = UserFactory()
        trip = services.create_trip(user, title="A trip")
        destination = DestinationFactory()
        stop = services.add_destination_to_trip(trip, destination)

        services.remove_trip_destination(stop)

        self.assertFalse(TripDestination.objects.filter(pk=stop.pk).exists())

    def test_get_trip_destination_ids(self):
        user = UserFactory()
        trip = services.create_trip(user, title="A trip")
        destination = DestinationFactory()
        services.add_destination_to_trip(trip, destination)

        self.assertEqual(services.get_trip_destination_ids(trip), {destination.id})
