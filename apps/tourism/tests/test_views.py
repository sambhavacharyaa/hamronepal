from django.test import TestCase

from apps.accounts.tests.factories import UserFactory
from apps.tourism.models import SavedPlace, Trip, TripDestination

from .factories import DestinationFactory


class PublicBrowsingTests(TestCase):
    def test_home_is_public(self):
        response = self.client.get("/en/tourism/")
        self.assertEqual(response.status_code, 200)

    def test_destination_list_is_public(self):
        DestinationFactory(title="Pokhara")
        response = self.client.get("/en/tourism/destinations/")
        self.assertContains(response, "Pokhara")

    def test_destination_detail_is_public(self):
        destination = DestinationFactory(title="Lumbini")
        response = self.client.get(f"/en/tourism/destinations/{destination.slug}/")
        self.assertContains(response, "Lumbini")

    def test_draft_destination_404s(self):
        destination = DestinationFactory(title="Unpublished Place")
        destination.status = destination.Status.DRAFT
        destination.save()
        response = self.client.get(f"/en/tourism/destinations/{destination.slug}/")
        self.assertEqual(response.status_code, 404)


class ToggleSavedViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.destination = DestinationFactory()

    def test_requires_login(self):
        response = self.client.post(f"/en/tourism/destinations/{self.destination.slug}/save/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_toggle_saves_then_unsaves(self):
        self.client.force_login(self.user)
        url = f"/en/tourism/destinations/{self.destination.slug}/save/"

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SavedPlace.objects.filter(user=self.user, destination=self.destination).exists())

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SavedPlace.objects.filter(user=self.user, destination=self.destination).exists())

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/en/tourism/destinations/{self.destination.slug}/save/")
        self.assertEqual(response.status_code, 405)


class SavedPlacesViewTests(TestCase):
    def test_requires_login(self):
        response = self.client.get("/en/tourism/saved/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_never_shows_another_users_saved_place(self):
        user = UserFactory()
        other_user = UserFactory()
        destination = DestinationFactory(title="Someone else's saved place")
        SavedPlace.objects.create(user=other_user, destination=destination)

        self.client.force_login(user)
        response = self.client.get("/en/tourism/saved/")

        self.assertNotContains(response, "Someone else's saved place")


class TripListViewTests(TestCase):
    def test_requires_login(self):
        response = self.client.get("/en/tourism/trips/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_never_shows_another_users_trip(self):
        user = UserFactory()
        other_user = UserFactory()
        Trip.objects.create(user=other_user, title="Someone else's trip")

        self.client.force_login(user)
        response = self.client.get("/en/tourism/trips/")

        self.assertNotContains(response, "Someone else's trip")


class TripCreateViewTests(TestCase):
    def test_requires_login(self):
        response = self.client.post("/en/tourism/trips/create/", {"title": "A trip"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_creates_trip_for_current_user(self):
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.post("/en/tourism/trips/create/", {"title": "My Nepal Trip"})

        trip = Trip.objects.get(user=user, title="My Nepal Trip")
        self.assertRedirects(response, f"/en/tourism/trips/{trip.pk}/")


class TripOwnershipIsolationTests(TestCase):
    def setUp(self):
        self.owner = UserFactory()
        self.intruder = UserFactory()
        self.trip = Trip.objects.create(user=self.owner, title="Owner's trip")
        self.destination = DestinationFactory()

    def test_intruder_cannot_view_trip(self):
        self.client.force_login(self.intruder)
        response = self.client.get(f"/en/tourism/trips/{self.trip.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_intruder_cannot_add_destination_to_trip(self):
        self.client.force_login(self.intruder)
        response = self.client.post(
            f"/en/tourism/trips/{self.trip.pk}/add/{self.destination.slug}/"
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(TripDestination.objects.filter(trip=self.trip).exists())

    def test_intruder_cannot_remove_destination_from_trip(self):
        stop = TripDestination.objects.create(trip=self.trip, destination=self.destination)
        self.client.force_login(self.intruder)

        response = self.client.post(f"/en/tourism/trips/{self.trip.pk}/remove/{stop.pk}/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(TripDestination.objects.filter(pk=stop.pk).exists())

    def test_intruder_cannot_delete_trip(self):
        self.client.force_login(self.intruder)
        response = self.client.post(f"/en/tourism/trips/{self.trip.pk}/delete/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Trip.objects.filter(pk=self.trip.pk).exists())

    def test_owner_can_add_and_remove_a_stop(self):
        self.client.force_login(self.owner)

        response = self.client.post(f"/en/tourism/trips/{self.trip.pk}/add/{self.destination.slug}/")
        self.assertEqual(response.status_code, 200)
        stop = TripDestination.objects.get(trip=self.trip, destination=self.destination)

        response = self.client.post(f"/en/tourism/trips/{self.trip.pk}/remove/{stop.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TripDestination.objects.filter(pk=stop.pk).exists())

    def test_added_destination_disappears_from_picker(self):
        self.client.force_login(self.owner)

        response = self.client.post(f"/en/tourism/trips/{self.trip.pk}/add/{self.destination.slug}/")

        self.assertNotContains(response, f"/add/{self.destination.slug}/")

    def test_removed_destination_reappears_in_picker(self):
        stop = TripDestination.objects.create(trip=self.trip, destination=self.destination)
        self.client.force_login(self.owner)

        response = self.client.post(f"/en/tourism/trips/{self.trip.pk}/remove/{stop.pk}/")

        self.assertContains(response, f"/add/{self.destination.slug}/")
