"""
Create a cron entry to run this command, e.g. every day at 02:00

0 2 * * * /path/to/venv/bin/python /path/to/project/manage.py purge_old_sessions >> /var/log/django_purge.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from demo.models import ToDo


class Command(BaseCommand):
    help = "Purge ToDo items older than 30 days"

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=30)
        count, _ = ToDo.objects.filter(modified__lt=cutoff).delete()
        self.stdout.write(
            f"Deleted {count} old ToDo items with sessions older than 30 days."
        )
