from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.dashboard import services
from apps.dashboard.models import Notification, RecentlyViewedProcess, SavedProcess, UserDocument
from apps.processes import services as process_services
from apps.processes.models import UserProcessProgress
from apps.processes.tests.factories import ProcessFactory, ProcessSourceFactory
from apps.tasks.models import Task


def publish(process, user):
    ProcessSourceFactory(process=process)
    process_services.publish_new_version(process, user)
    return process


class ClassifyUrgencyTests(TestCase):
    def test_negative_is_overdue(self):
        self.assertEqual(services.classify_urgency(-1), "overdue")

    def test_zero_to_seven_is_urgent(self):
        self.assertEqual(services.classify_urgency(0), "urgent")
        self.assertEqual(services.classify_urgency(7), "urgent")

    def test_eight_to_thirty_is_soon(self):
        self.assertEqual(services.classify_urgency(8), "soon")
        self.assertEqual(services.classify_urgency(30), "soon")

    def test_above_thirty_is_later(self):
        self.assertEqual(services.classify_urgency(31), "later")


class DescribeExpiryTests(TestCase):
    def test_overdue_phrasing(self):
        self.assertEqual(services.describe_expiry(-1), "expired 1 day ago")
        self.assertEqual(services.describe_expiry(-3), "expired 3 days ago")

    def test_today_phrasing(self):
        self.assertEqual(services.describe_expiry(0), "expires today")

    def test_day_phrasing_under_sixty_days(self):
        self.assertEqual(services.describe_expiry(1), "expires in 1 day")
        self.assertEqual(services.describe_expiry(32), "expires in 32 days")

    def test_month_phrasing_at_and_above_sixty_days(self):
        self.assertEqual(services.describe_expiry(60), "expires in 2 months")
        self.assertEqual(services.describe_expiry(120), "expires in 4 months")


class DescribeDueTests(TestCase):
    def test_overdue_phrasing(self):
        self.assertEqual(services.describe_due(-2), "was due 2 days ago")

    def test_today_and_future_phrasing(self):
        self.assertEqual(services.describe_due(0), "is due today")
        self.assertEqual(services.describe_due(5), "is due in 5 days")


class ToggleSavedProcessTests(TestCase):
    def test_toggle_saves_then_unsaves(self):
        user = UserFactory()
        process = ProcessFactory()

        is_saved = services.toggle_saved_process(user, process)
        self.assertTrue(is_saved)
        self.assertTrue(SavedProcess.objects.filter(user=user, process=process).exists())

        is_saved = services.toggle_saved_process(user, process)
        self.assertFalse(is_saved)
        self.assertFalse(SavedProcess.objects.filter(user=user, process=process).exists())

    def test_records_the_version_at_save_time(self):
        user = UserFactory()
        process = publish(ProcessFactory(), user)

        services.toggle_saved_process(user, process)

        saved = SavedProcess.objects.get(user=user, process=process)
        self.assertEqual(saved.version_at_save, process.current_version_number)


class GetSavedProcessIdsTests(TestCase):
    def test_returns_empty_set_for_anonymous_user(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(services.get_saved_process_ids(AnonymousUser()), set())

    def test_returns_only_this_users_saved_ids(self):
        user = UserFactory()
        other_user = UserFactory()
        process = ProcessFactory()
        SavedProcess.objects.create(user=user, process=process)
        SavedProcess.objects.create(user=other_user, process=ProcessFactory())

        self.assertEqual(services.get_saved_process_ids(user), {process.id})


class RecordProcessViewTests(TestCase):
    def test_creates_then_touches_existing_row(self):
        user = UserFactory()
        process = ProcessFactory()

        services.record_process_view(user, process)
        self.assertEqual(RecentlyViewedProcess.objects.filter(user=user, process=process).count(), 1)
        first_seen = RecentlyViewedProcess.objects.get(user=user, process=process).updated_at

        services.record_process_view(user, process)
        self.assertEqual(RecentlyViewedProcess.objects.filter(user=user, process=process).count(), 1)
        self.assertGreaterEqual(
            RecentlyViewedProcess.objects.get(user=user, process=process).updated_at, first_seen
        )


class GetDeadlinesTests(TestCase):
    def test_merges_and_sorts_tasks_and_documents(self):
        user = UserFactory()
        today = timezone.localdate()

        Task.objects.create(user=user, title="Later task", due_date=today + timedelta(days=10))
        Task.objects.create(user=user, title="Sooner task", due_date=today + timedelta(days=2))
        UserDocument.objects.create(user=user, title="A document", expiry_date=today + timedelta(days=5))
        Task.objects.create(user=user, title="No due date")

        deadlines = services.get_deadlines(user)

        self.assertEqual([d["title"] for d in deadlines], ["Sooner task", "A document", "Later task"])
        self.assertEqual(deadlines[0]["kind"], "task")
        self.assertEqual(deadlines[1]["kind"], "document")

    def test_marks_overdue_items(self):
        user = UserFactory()
        today = timezone.localdate()
        Task.objects.create(user=user, title="Overdue task", due_date=today - timedelta(days=1))

        deadlines = services.get_deadlines(user)

        self.assertTrue(deadlines[0]["is_overdue"])
        self.assertEqual(deadlines[0]["urgency"], "overdue")

    def test_excludes_completed_tasks_by_default(self):
        user = UserFactory()
        today = timezone.localdate()
        Task.objects.create(user=user, title="Done", due_date=today + timedelta(days=1), is_completed=True)

        self.assertEqual(services.get_deadlines(user), [])

    def test_include_completed_appends_completed_tasks(self):
        user = UserFactory()
        today = timezone.localdate()
        Task.objects.create(user=user, title="Done", due_date=today - timedelta(days=1), is_completed=True)

        deadlines = services.get_deadlines(user, include_completed=True)

        self.assertEqual(len(deadlines), 1)
        self.assertTrue(deadlines[0]["is_completed"])

    def test_within_days_caps_the_horizon(self):
        user = UserFactory()
        today = timezone.localdate()
        Task.objects.create(user=user, title="Far away", due_date=today + timedelta(days=90))

        self.assertEqual(services.get_deadlines(user, within_days=60), [])
        self.assertEqual(len(services.get_deadlines(user, within_days=None)), 1)


class FilterDeadlinesTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def _deadline(self, days_until, is_completed=False, completed_at=None):
        return {
            "kind": "task",
            "title": f"item {days_until}",
            "date": self.today + timedelta(days=days_until),
            "url": None,
            "days_until": days_until,
            "is_overdue": days_until < 0,
            "is_completed": is_completed,
            "completed_at": completed_at,
            "urgency": services.classify_urgency(days_until),
        }

    def test_upcoming_excludes_overdue_and_completed(self):
        deadlines = [self._deadline(-1), self._deadline(3), self._deadline(3, is_completed=True)]
        result = services.filter_deadlines(deadlines, "upcoming")
        self.assertEqual([d["days_until"] for d in result], [3])

    def test_this_week_is_zero_to_seven(self):
        deadlines = [self._deadline(0), self._deadline(7), self._deadline(8), self._deadline(-1)]
        result = services.filter_deadlines(deadlines, "this_week")
        self.assertEqual({d["days_until"] for d in result}, {0, 7})

    def test_this_month_is_eight_to_thirty(self):
        deadlines = [self._deadline(7), self._deadline(8), self._deadline(30), self._deadline(31)]
        result = services.filter_deadlines(deadlines, "this_month")
        self.assertEqual({d["days_until"] for d in result}, {8, 30})

    def test_later_is_above_thirty(self):
        deadlines = [self._deadline(30), self._deadline(31)]
        result = services.filter_deadlines(deadlines, "later")
        self.assertEqual({d["days_until"] for d in result}, {31})

    def test_overdue_excludes_completed(self):
        deadlines = [self._deadline(-1), self._deadline(-2, is_completed=True)]
        result = services.filter_deadlines(deadlines, "overdue")
        self.assertEqual({d["days_until"] for d in result}, {-1})

    def test_completed_sorts_most_recent_first(self):
        older = self._deadline(-5, is_completed=True, completed_at=timezone.now() - timedelta(days=5))
        newer = self._deadline(-1, is_completed=True, completed_at=timezone.now() - timedelta(days=1))
        result = services.filter_deadlines([older, newer], "completed")
        self.assertEqual([d["title"] for d in result], [newer["title"], older["title"]])


class SyncNotificationsTests(TestCase):
    def test_generates_notification_for_document_within_the_tightest_threshold(self):
        user = UserFactory()
        today = timezone.localdate()
        document = UserDocument.objects.create(
            user=user, title="Citizenship certificate", expiry_date=today + timedelta(days=5)
        )

        services.sync_notifications(user)

        notification = Notification.objects.get(user=user, dedupe_key=f"document_expiry_{document.id}_7")
        self.assertIn("Citizenship certificate", notification.message)
        self.assertEqual(notification.category, Notification.Category.DOCUMENT_EXPIRY)
        self.assertEqual(notification.related_document, document)

    def test_far_out_document_gets_the_ninety_day_threshold(self):
        user = UserFactory()
        today = timezone.localdate()
        document = UserDocument.objects.create(user=user, title="Passport", expiry_date=today + timedelta(days=32))

        services.sync_notifications(user)

        notification = Notification.objects.get(user=user, dedupe_key=f"document_expiry_{document.id}_90")
        self.assertIn("expires in 32 days", notification.message)

    def test_document_beyond_ninety_days_gets_no_notification(self):
        user = UserFactory()
        today = timezone.localdate()
        UserDocument.objects.create(user=user, title="Far off", expiry_date=today + timedelta(days=200))

        services.sync_notifications(user)

        self.assertEqual(Notification.objects.filter(user=user).count(), 0)

    def test_already_expired_document_is_danger_level(self):
        user = UserFactory()
        today = timezone.localdate()
        document = UserDocument.objects.create(user=user, title="Old license", expiry_date=today - timedelta(days=3))

        services.sync_notifications(user)

        notification = Notification.objects.get(user=user, dedupe_key=f"document_expiry_{document.id}_0")
        self.assertEqual(notification.level, Notification.Level.DANGER)
        self.assertIn("expired 3 days ago", notification.message)

    def test_escalating_thresholds_do_not_duplicate_and_do_not_suppress_each_other(self):
        user = UserFactory()
        today = timezone.localdate()
        document = UserDocument.objects.create(user=user, title="Citizenship certificate", expiry_date=today + timedelta(days=32))

        services.sync_notifications(user)
        self.assertEqual(Notification.objects.filter(user=user).count(), 1)
        first = Notification.objects.get(user=user)
        services.dismiss_notification(first)

        services.sync_notifications(user)
        self.assertEqual(Notification.objects.filter(user=user).count(), 1)

        document.expiry_date = today + timedelta(days=5)
        document.save(update_fields=["expiry_date"])
        services.sync_notifications(user)

        self.assertEqual(Notification.objects.filter(user=user).count(), 2)
        self.assertTrue(Notification.objects.get(dedupe_key=f"document_expiry_{document.id}_90").is_dismissed)
        self.assertFalse(Notification.objects.get(dedupe_key=f"document_expiry_{document.id}_7").is_dismissed)

    def test_generates_notification_for_overdue_task(self):
        user = UserFactory()
        today = timezone.localdate()
        task = Task.objects.create(user=user, title="Book appointment", due_date=today - timedelta(days=1))

        services.sync_notifications(user)

        notification = Notification.objects.get(user=user, dedupe_key=f"task_due_{task.id}_0")
        self.assertEqual(notification.category, Notification.Category.TASK_DUE)
        self.assertEqual(notification.related_task, task)
        self.assertIn("was due 1 day ago", notification.message)

    def test_completed_tasks_never_generate_notifications(self):
        user = UserFactory()
        today = timezone.localdate()
        Task.objects.create(user=user, title="Done", due_date=today - timedelta(days=1), is_completed=True)

        services.sync_notifications(user)

        self.assertEqual(Notification.objects.filter(user=user, category=Notification.Category.TASK_DUE).count(), 0)

    def test_is_idempotent_and_does_not_duplicate(self):
        user = UserFactory()
        today = timezone.localdate()
        UserDocument.objects.create(user=user, title="Citizenship certificate", expiry_date=today + timedelta(days=5))

        services.sync_notifications(user)
        services.sync_notifications(user)

        self.assertEqual(Notification.objects.filter(user=user).count(), 1)

    def test_does_not_resurrect_dismissed_notification(self):
        user = UserFactory()
        today = timezone.localdate()
        document = UserDocument.objects.create(
            user=user, title="Citizenship certificate", expiry_date=today + timedelta(days=5)
        )

        services.sync_notifications(user)
        notification = Notification.objects.get(user=user, dedupe_key=f"document_expiry_{document.id}_7")
        services.dismiss_notification(notification)

        services.sync_notifications(user)

        notification.refresh_from_db()
        self.assertTrue(notification.is_dismissed)
        self.assertEqual(Notification.objects.filter(user=user).count(), 1)

    def test_ignores_documents_without_an_expiry_date(self):
        user = UserFactory()
        UserDocument.objects.create(user=user, title="No expiry")

        services.sync_notifications(user)

        self.assertEqual(Notification.objects.filter(user=user).count(), 0)

    def test_generates_notification_for_stalled_process(self):
        user = UserFactory()
        process = publish(ProcessFactory(), user)
        progress = process_services.start_tracking(user, process, None)
        UserProcessProgress.objects.filter(pk=progress.pk).update(
            updated_at=timezone.now() - timedelta(days=20)
        )

        services.sync_notifications(user)

        notification = Notification.objects.get(user=user, dedupe_key=f"stalled_process_{progress.id}")
        self.assertEqual(notification.category, Notification.Category.PROCESS_STALLED)

    def test_generates_progress_milestone_notification_once(self):
        from apps.processes.tests.factories import ProcessStepFactory

        user = UserFactory()
        process = publish(ProcessFactory(), user)
        for i in range(4):
            ProcessStepFactory(process=process, order=i + 2)
        progress = process_services.start_tracking(user, process, None)

        for step_progress in progress.step_progress.all()[:2]:
            step_progress.is_completed = True
            step_progress.save(update_fields=["is_completed"])

        services.sync_notifications(user)
        services.sync_notifications(user)

        notifications = Notification.objects.filter(
            user=user, category=Notification.Category.PROCESS_PROGRESS
        )
        self.assertEqual(notifications.count(), 1)
        self.assertIn("2/4 steps completed", notifications.first().message)

    def test_saved_process_update_fires_once_per_new_version(self):
        user = UserFactory()
        process = publish(ProcessFactory(), user)
        services.toggle_saved_process(user, process)

        services.sync_notifications(user)
        self.assertEqual(
            Notification.objects.filter(user=user, category=Notification.Category.PROCESS_UPDATE).count(), 0
        )

        process_services.publish_new_version(process, user)
        services.sync_notifications(user)
        services.sync_notifications(user)

        notifications = Notification.objects.filter(user=user, category=Notification.Category.PROCESS_UPDATE)
        self.assertEqual(notifications.count(), 1)


class MarkNotificationTests(TestCase):
    def test_mark_read_sets_timestamp(self):
        notification = Notification.objects.create(user=UserFactory(), message="Hi", dedupe_key="x")
        services.mark_notification_read(notification)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_mark_all_read_only_touches_this_users_unread(self):
        user = UserFactory()
        other_user = UserFactory()
        Notification.objects.create(user=user, message="A", dedupe_key="a")
        Notification.objects.create(user=user, message="B", dedupe_key="b", is_read=True)
        Notification.objects.create(user=other_user, message="C", dedupe_key="c")

        updated = services.mark_all_notifications_read(user)

        self.assertEqual(updated, 1)
        self.assertTrue(Notification.objects.get(dedupe_key="a").is_read)
        self.assertFalse(Notification.objects.get(dedupe_key="c").is_read)

    def test_unread_count_excludes_dismissed_and_read(self):
        user = UserFactory()
        Notification.objects.create(user=user, message="A", dedupe_key="a")
        Notification.objects.create(user=user, message="B", dedupe_key="b", is_read=True)
        Notification.objects.create(user=user, message="C", dedupe_key="c", is_dismissed=True)

        self.assertEqual(services.get_unread_notification_count(user), 1)


class DismissNotificationTests(TestCase):
    def test_marks_dismissed_with_timestamp(self):
        notification = Notification.objects.create(user=UserFactory(), message="Hi", dedupe_key="x")
        services.dismiss_notification(notification)
        notification.refresh_from_db()
        self.assertTrue(notification.is_dismissed)
        self.assertIsNotNone(notification.dismissed_at)


class GetRecommendedProcessesTests(TestCase):
    def test_excludes_processes_the_user_already_tracks(self):
        user = UserFactory()
        tracked = publish(ProcessFactory(title="Tracked"), user)
        untracked = publish(ProcessFactory(title="Untracked"), user)
        process_services.start_tracking(user, tracked, None)

        recommended = services.get_recommended_processes(user)

        self.assertIn(untracked, recommended)
        self.assertNotIn(tracked, recommended)

    def test_respects_limit(self):
        user = UserFactory()
        for i in range(5):
            publish(ProcessFactory(title=f"Process {i}"), user)

        recommended = services.get_recommended_processes(user, limit=2)

        self.assertEqual(len(recommended), 2)


class GetDashboardContextTests(TestCase):
    def test_separates_active_and_completed_progress(self):
        user = UserFactory()
        active_process = publish(ProcessFactory(title="Active"), user)
        completed_process = publish(ProcessFactory(title="Done"), user)
        process_services.start_tracking(user, active_process, None)
        completed_progress = process_services.start_tracking(user, completed_process, None)
        completed_progress.status = UserProcessProgress.Status.COMPLETED
        completed_progress.save(update_fields=["status"])

        context = services.get_dashboard_context(user)

        active_titles = [p.process.title for p in context["active_progress"]]
        completed_titles = [p.process.title for p in context["completed_progress"]]
        self.assertIn("Active", active_titles)
        self.assertNotIn("Done", active_titles)
        self.assertIn("Done", completed_titles)

    def test_priority_tasks_excludes_completed(self):
        user = UserFactory()
        Task.objects.create(user=user, title="Open task")
        Task.objects.create(user=user, title="Done task", is_completed=True)

        context = services.get_dashboard_context(user)

        priority_titles = [t.title for t in context["priority_tasks"]]
        self.assertIn("Open task", priority_titles)
        self.assertNotIn("Done task", priority_titles)

    def test_flags_expiring_and_expired_documents(self):
        user = UserFactory()
        today = date.today()
        UserDocument.objects.create(user=user, title="Soon", expiry_date=today + timedelta(days=10))
        UserDocument.objects.create(user=user, title="Gone", expiry_date=today - timedelta(days=1))
        UserDocument.objects.create(user=user, title="Fine", expiry_date=today + timedelta(days=200))

        context = services.get_dashboard_context(user)
        by_title = {d.title: d for d in context["documents"]}

        self.assertTrue(by_title["Soon"].is_expiring_soon)
        self.assertFalse(by_title["Soon"].is_expired)
        self.assertTrue(by_title["Gone"].is_expired)
        self.assertFalse(by_title["Fine"].is_expiring_soon)
        self.assertFalse(by_title["Fine"].is_expired)

    def test_only_includes_this_users_data(self):
        user = UserFactory()
        other_user = UserFactory()
        SavedProcess.objects.create(user=other_user, process=ProcessFactory())
        UserDocument.objects.create(user=other_user, title="Not yours")
        Notification.objects.create(user=other_user, message="Not yours", dedupe_key="x")

        context = services.get_dashboard_context(user)

        self.assertEqual(list(context["saved_processes"]), [])
        self.assertEqual(list(context["documents"]), [])
        self.assertEqual(list(context["notifications_preview"]), [])

    def test_stats_with_no_active_journeys(self):
        user = UserFactory()

        context = services.get_dashboard_context(user)

        self.assertEqual(context["stats"]["active_journey_count"], 0)
        self.assertIsNone(context["stats"]["average_progress_percent"])

    def test_stats_average_progress_across_active_journeys(self):
        from apps.processes.tests.factories import ProcessRequirementFactory, ProcessStepFactory

        user = UserFactory()
        process_a = publish(ProcessFactory(title="A"), user)
        ProcessStepFactory(process=process_a, order=1)
        ProcessRequirementFactory(process=process_a, order=1)
        process_b = publish(ProcessFactory(title="B"), user)
        ProcessStepFactory(process=process_b, order=1)
        ProcessRequirementFactory(process=process_b, order=1)

        progress_a = process_services.start_tracking(user, process_a, None)
        progress_a.step_progress.update(is_completed=True)
        progress_a.requirement_progress.update(is_completed=True)
        process_services.start_tracking(user, process_b, None)

        context = services.get_dashboard_context(user)

        self.assertEqual(context["stats"]["active_journey_count"], 2)
        self.assertEqual(context["stats"]["average_progress_percent"], 50)

    def test_stats_counts_pending_tasks_expiring_documents_and_completed(self):
        user = UserFactory()
        Task.objects.create(user=user, title="Open")
        Task.objects.create(user=user, title="Done", is_completed=True)
        UserDocument.objects.create(user=user, title="Soon", expiry_date=date.today() + timedelta(days=5))
        process = publish(ProcessFactory(), user)
        progress = process_services.start_tracking(user, process, None)
        progress.status = UserProcessProgress.Status.COMPLETED
        progress.save(update_fields=["status"])

        context = services.get_dashboard_context(user)

        self.assertEqual(context["stats"]["pending_task_count"], 1)
        self.assertEqual(context["stats"]["expiring_soon_count"], 1)
        self.assertEqual(context["stats"]["completed_count"], 1)


class ComputeRingDashoffsetTests(TestCase):
    def test_zero_percent_is_full_offset(self):
        self.assertEqual(services.compute_ring_dashoffset(0), round(services.RING_CIRCUMFERENCE, 2))

    def test_hundred_percent_is_zero_offset(self):
        self.assertEqual(services.compute_ring_dashoffset(100), 0)

    def test_clamps_out_of_range_values(self):
        self.assertEqual(services.compute_ring_dashoffset(-10), round(services.RING_CIRCUMFERENCE, 2))
        self.assertEqual(services.compute_ring_dashoffset(150), 0)
