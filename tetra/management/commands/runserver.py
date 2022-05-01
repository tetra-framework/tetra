from django.conf import settings

if "django.contrib.staticfiles" in settings.INSTALLED_APPS:
    from django.contrib.staticfiles.management.commands.runserver import (
        Command as BaseRunserverCommand,
    )
else:
    from django.core.management.commands.runserver import (
        Command as BaseRunserverCommand,
    )

from ...build import runserver_build


class Command(BaseRunserverCommand):
    def inner_run(self, *args, **options):
        runserver_build()
        super().inner_run(*args, **options)
