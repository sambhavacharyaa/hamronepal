import factory

from apps.tourism.models import Destination, DestinationCategory, DestinationHighlight, Season


class DestinationCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DestinationCategory
        django_get_or_create = ("slug",)

    name = "Nature & Wildlife"
    slug = "nature-wildlife"


class DestinationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Destination

    title = factory.Sequence(lambda n: f"Test Destination {n}")
    slug = factory.Sequence(lambda n: f"test-destination-{n}")
    category = factory.SubFactory(DestinationCategoryFactory)
    region = "Test Region"
    summary = "A test destination for the test suite."
    status = Destination.Status.PUBLISHED
    best_season = Season.AUTUMN


class DestinationHighlightFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DestinationHighlight

    destination = factory.SubFactory(DestinationFactory)
    order = factory.Sequence(lambda n: n + 1)
    title = factory.Sequence(lambda n: f"Highlight {n}")
