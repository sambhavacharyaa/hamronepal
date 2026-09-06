from django.core import mail
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.tourism.models import SavedPlace, Trip, TripDestination

from .factories import DestinationFactory


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class AnonymousToTripPlanningSmokeTest(TestCase):
    def setUp(self):
        self.destination = DestinationFactory(title="Chitwan National Park", region="Chitwan, Terai")

    def test_full_journey(self):
        client = self.client

        response = client.get("/en/tourism/")
        self.assertEqual(response.status_code, 200)

        response = client.get("/en/tourism/destinations/", {"q": "chitwan"})
        self.assertContains(response, "Chitwan National Park")

        response = client.get(f"/en/tourism/destinations/{self.destination.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Save this place")

        response = client.post(
            "/en/accounts/register/",
            {"email": "traveler@example.com", "password1": "S0meStrongPass!", "password2": "S0meStrongPass!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        user = User.objects.get(email="traveler@example.com")

        response = client.post(f"/en/tourism/destinations/{self.destination.slug}/save/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SavedPlace.objects.filter(user=user, destination=self.destination).exists())

        response = client.post("/en/tourism/trips/create/", {"title": "Autumn Nepal Trip"})
        trip = Trip.objects.get(user=user, title="Autumn Nepal Trip")
        self.assertRedirects(response, f"/en/tourism/trips/{trip.pk}/")

        response = client.post(f"/en/tourism/trips/{trip.pk}/add/{self.destination.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(TripDestination.objects.filter(trip=trip, destination=self.destination).exists())

        response = client.get(f"/en/tourism/trips/{trip.pk}/")
        self.assertContains(response, "Chitwan National Park")
