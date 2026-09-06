from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.tourism.models import RecentlyViewedDestination, SavedPlace, Trip, TripDestination

from .factories import DestinationFactory


class SavedPlaceModelTests(TestCase):
    def test_str(self):
        user = UserFactory(email="traveler@example.com")
        destination = DestinationFactory(title="Pokhara")
        saved = SavedPlace.objects.create(user=user, destination=destination)
        self.assertIn("traveler@example.com", str(saved))
        self.assertIn("Pokhara", str(saved))

    def test_user_cannot_save_same_destination_twice(self):
        user = UserFactory()
        destination = DestinationFactory()
        SavedPlace.objects.create(user=user, destination=destination)
        with self.assertRaises(IntegrityError):
            SavedPlace.objects.create(user=user, destination=destination)


class RecentlyViewedDestinationModelTests(TestCase):
    def test_user_cannot_have_duplicate_recently_viewed_rows(self):
        user = UserFactory()
        destination = DestinationFactory()
        RecentlyViewedDestination.objects.create(user=user, destination=destination)
        with self.assertRaises(IntegrityError):
            RecentlyViewedDestination.objects.create(user=user, destination=destination)


class TripModelTests(TestCase):
    def test_str_is_title(self):
        trip = Trip.objects.create(user=UserFactory(), title="Autumn Nepal Trip")
        self.assertEqual(str(trip), "Autumn Nepal Trip")


class TripDestinationModelTests(TestCase):
    def test_ordering_follows_order_field(self):
        trip = Trip.objects.create(user=UserFactory(), title="A trip")
        second = DestinationFactory(title="Second stop")
        first = DestinationFactory(title="First stop")
        TripDestination.objects.create(trip=trip, destination=second, order=1)
        TripDestination.objects.create(trip=trip, destination=first, order=0)

        stops = list(trip.stops.all())

        self.assertEqual(stops[0].destination, first)
        self.assertEqual(stops[1].destination, second)
