from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.processes import services
from apps.processes.models import ProcessVariant, ProcessVersion, UserProcessProgress

from .factories import (
    ProcessFactory,
    ProcessRequirementFactory,
    ProcessSourceFactory,
    ProcessStepFactory,
)


class PublishNewVersionTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.process = ProcessFactory()
        ProcessStepFactory(process=self.process, order=1)

    def test_publish_without_sources_raises(self):
        with self.assertRaises(services.PublishError):
            services.publish_new_version(self.process, self.user)
        self.assertFalse(ProcessVersion.objects.filter(process=self.process).exists())

    def test_publish_with_source_succeeds(self):
        ProcessSourceFactory(process=self.process)

        version = services.publish_new_version(self.process, self.user, changelog="first")

        self.process.refresh_from_db()
        self.assertEqual(self.process.status, self.process.Status.PUBLISHED)
        self.assertEqual(self.process.current_version_number, "1")
        self.assertEqual(self.process.last_verified_at, timezone.localdate())
        self.assertEqual(version.version_number, "1")
        self.assertEqual(version.snapshot["title"], self.process.title)
        self.assertEqual(len(version.snapshot["steps"]), 1)

    def test_publishing_twice_increments_version_number(self):
        ProcessSourceFactory(process=self.process)
        services.publish_new_version(self.process, self.user)
        second = services.publish_new_version(self.process, self.user)

        self.assertEqual(second.version_number, "2")
        self.assertEqual(ProcessVersion.objects.filter(process=self.process).count(), 2)


class StartTrackingTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.process = ProcessFactory()
        self.step_all = ProcessStepFactory(process=self.process, order=1, variant=ProcessVariant.ALL)
        self.step_individual = ProcessStepFactory(
            process=self.process, order=2, variant=ProcessVariant.INDIVIDUAL
        )
        self.step_business = ProcessStepFactory(process=self.process, order=3, variant=ProcessVariant.BUSINESS)
        self.req_all = ProcessRequirementFactory(process=self.process, order=1, variant=ProcessVariant.ALL)
        self.req_business = ProcessRequirementFactory(
            process=self.process, order=2, variant=ProcessVariant.BUSINESS
        )

    def test_start_tracking_without_variant_includes_all_items(self):
        progress = services.start_tracking(self.user, self.process, None)

        self.assertEqual(progress.status, UserProcessProgress.Status.NOT_STARTED)
        self.assertEqual(progress.step_progress.count(), 3)
        self.assertEqual(progress.requirement_progress.count(), 2)

    def test_start_tracking_with_individual_variant_excludes_business_only_items(self):
        progress = services.start_tracking(self.user, self.process, ProcessVariant.INDIVIDUAL)

        step_ids = set(progress.step_progress.values_list("step_id", flat=True))
        self.assertEqual(step_ids, {self.step_all.id, self.step_individual.id})
        requirement_ids = set(progress.requirement_progress.values_list("requirement_id", flat=True))
        self.assertEqual(requirement_ids, {self.req_all.id})

    def test_start_tracking_is_idempotent(self):
        first = services.start_tracking(self.user, self.process, ProcessVariant.BUSINESS)
        second = services.start_tracking(self.user, self.process, ProcessVariant.BUSINESS)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(UserProcessProgress.objects.filter(user=self.user, process=self.process).count(), 1)
        self.assertEqual(first.step_progress.count(), 2)

    def test_two_users_get_independent_progress(self):
        other_user = UserFactory()
        progress1 = services.start_tracking(self.user, self.process, ProcessVariant.INDIVIDUAL)
        progress2 = services.start_tracking(other_user, self.process, ProcessVariant.BUSINESS)

        self.assertNotEqual(progress1.pk, progress2.pk)
        self.assertEqual(
            set(progress1.step_progress.values_list("step_id", flat=True)),
            {self.step_all.id, self.step_individual.id},
        )
        self.assertEqual(
            set(progress2.step_progress.values_list("step_id", flat=True)),
            {self.step_all.id, self.step_business.id},
        )


class ToggleAndStatusTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.process = ProcessFactory()
        self.step = ProcessStepFactory(process=self.process, order=1)
        self.requirement = ProcessRequirementFactory(process=self.process, order=1)
        self.progress = services.start_tracking(self.user, self.process, None)

    def test_toggling_a_step_marks_it_complete_and_advances_status(self):
        step_progress = services.toggle_step_progress(self.progress, self.step)

        self.assertTrue(step_progress.is_completed)
        self.assertIsNotNone(step_progress.completed_at)
        self.progress.refresh_from_db()
        self.assertEqual(self.progress.status, UserProcessProgress.Status.PREPARING)

    def test_untoggling_a_step_does_not_revert_status(self):
        services.toggle_step_progress(self.progress, self.step)
        step_progress = services.toggle_step_progress(self.progress, self.step)

        self.assertFalse(step_progress.is_completed)
        self.assertIsNone(step_progress.completed_at)
        self.progress.refresh_from_db()
        self.assertEqual(self.progress.status, UserProcessProgress.Status.PREPARING)

    def test_toggling_a_requirement_works(self):
        requirement_progress = services.toggle_requirement_progress(self.progress, self.requirement)
        self.assertTrue(requirement_progress.is_completed)

    def test_advance_status_through_milestones(self):
        services.advance_status(self.progress, UserProcessProgress.Status.APPLIED)
        self.progress.refresh_from_db()
        self.assertEqual(self.progress.status, UserProcessProgress.Status.APPLIED)
        self.assertIsNone(self.progress.completed_at)

        services.advance_status(self.progress, UserProcessProgress.Status.COMPLETED)
        self.progress.refresh_from_db()
        self.assertEqual(self.progress.status, UserProcessProgress.Status.COMPLETED)
        self.assertIsNotNone(self.progress.completed_at)

    def test_advance_status_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            services.advance_status(self.progress, "not-a-real-status")

    def test_compute_percent(self):
        self.assertEqual(services.compute_percent(self.progress), 0)
        services.toggle_step_progress(self.progress, self.step)
        self.assertEqual(services.compute_percent(self.progress), 50)
        services.toggle_requirement_progress(self.progress, self.requirement)
        self.assertEqual(services.compute_percent(self.progress), 100)
