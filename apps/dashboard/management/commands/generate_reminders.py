from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.dashboard import services
from apps.dashboard.models import Notification


class Command(BaseCommand):
    help = (
        "Generates deadline and reminder notifications for all active users. "
        "Intended to be invoked on a schedule by an external cron (this project has no in-process scheduler); "
        "the dashboard also runs this per-request as a reliability fallback."
    )

    def handle(self, *args, **options):
        users = User.objects.filter(is_active=True)
        before = Notification.objects.count()
        for user in users:
            services.sync_notifications(user)
        created = Notification.objects.count() - before
        self.stdout.write(self.style.SUCCESS(f"Processed {users.count()} user(s), created {created} notification(s)."))
