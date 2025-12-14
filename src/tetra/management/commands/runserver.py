import sys

from django.conf import settings
from django.core.management import CommandError
from django.core.management.commands.runserver import Command as BaseRunserverCommand
from tetra.build import runserver_build


class Command(BaseRunserverCommand):
    # def inner_run(self, *args, **options):
    #     runserver_build()
    #     super().inner_run(*args, **options)

    def handle(self, *args, **options):
        runserver_build()
        # instead of super().handle(*args, **options)
        self.call_next_runserver(*args, **options)

    def call_next_runserver(self, *args, **options):
        from django.core.management import load_command_class

        # Get list of all apps excluding 'tetra*'
        apps = [app for app in settings.INSTALLED_APPS if not app.startswith("tetra")]
        # add 'django.core' as fallback, if even staticfiles is not there
        apps.append("django.core")

        for app_name in apps:
            try:
                # Attempt to load runserver from next app
                cmd = load_command_class(app_name, "runserver")
                cmd.run_from_argv(sys.argv)
                return
            except ModuleNotFoundError:
                continue
            except AttributeError:
                continue

        raise CommandError("No 'runserver' command found in any of the INSTALLED_APPS.")
