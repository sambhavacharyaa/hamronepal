from django.db import IntegrityError
from django.test import TestCase

from .factories import (
    ProcessCategoryFactory,
    ProcessFactory,
    ProcessFAQFactory,
    ProcessRequirementFactory,
    ProcessSourceFactory,
    ProcessStepFactory,
)


class ProcessModelTests(TestCase):
    def test_str_methods(self):
        category = ProcessCategoryFactory()
        process = ProcessFactory(title="Register a Thing", category=category)
        step = ProcessStepFactory(process=process, order=1, title="Do the first thing")
        requirement = ProcessRequirementFactory(process=process, name="A document")
        faq = ProcessFAQFactory(process=process, question="Is this real?")

        self.assertEqual(str(category), category.name)
        self.assertEqual(str(process), "Register a Thing")
        self.assertIn("Do the first thing", str(step))
        self.assertEqual(str(requirement), "A document")
        self.assertEqual(str(faq), "Is this real?")

    def test_process_defaults_to_draft(self):
        process = ProcessFactory()
        self.assertEqual(process.status, process.Status.DRAFT)

    def test_step_order_is_unique_per_process(self):
        process = ProcessFactory()
        ProcessStepFactory(process=process, order=1)
        with self.assertRaises(IntegrityError):
            ProcessStepFactory(process=process, order=1)

    def test_requirement_defaults_to_mandatory(self):
        requirement = ProcessRequirementFactory()
        self.assertTrue(requirement.is_mandatory)

    def test_source_str_is_title(self):
        source = ProcessSourceFactory(title="Official portal")
        self.assertEqual(str(source), "Official portal")
