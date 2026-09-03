from datetime import date

import factory

from apps.processes.models import (
    Process,
    ProcessCategory,
    ProcessFAQ,
    ProcessRequirement,
    ProcessSource,
    ProcessStep,
)


class ProcessCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProcessCategory
        django_get_or_create = ("slug",)

    name = "Business"
    slug = "business"


class ProcessFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Process

    title = factory.Sequence(lambda n: f"Test Process {n}")
    slug = factory.Sequence(lambda n: f"test-process-{n}")
    category = factory.SubFactory(ProcessCategoryFactory)
    summary = "A test process for the test suite."


class ProcessStepFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProcessStep

    process = factory.SubFactory(ProcessFactory)
    order = factory.Sequence(lambda n: n + 1)
    title = factory.Sequence(lambda n: f"Step {n}")


class ProcessRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProcessRequirement

    process = factory.SubFactory(ProcessFactory)
    order = factory.Sequence(lambda n: n + 1)
    name = factory.Sequence(lambda n: f"Requirement {n}")


class ProcessFAQFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProcessFAQ

    process = factory.SubFactory(ProcessFactory)
    order = factory.Sequence(lambda n: n + 1)
    question = factory.Sequence(lambda n: f"Question {n}?")
    answer = "An answer."


class ProcessSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProcessSource

    process = factory.SubFactory(ProcessFactory)
    title = "Official source"
    url = "https://example.gov.np"
    last_verified_date = factory.LazyFunction(date.today)
