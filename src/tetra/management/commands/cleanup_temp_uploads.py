from django.core.management.base import BaseCommand
from tetra.utils import cleanup_temp_uploads
from django.utils.translation import gettext as _


class Command(BaseCommand):
    help = _("Clean up old Tetra temporary upload files (default: older than 24 hrs.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-age-hours",
            type=int,
            default=24,
            help=_("Maximum age of temporary files in hours (default: 24)"),
        )

    def handle(self, *args, **options):
        count = cleanup_temp_uploads(options["max_age_hours"])
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(_("No temporary upload files found to clean up."))
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                _("Successfully cleaned up {count} temporary upload files.").format(
                    count=count
                )
            )
        )
