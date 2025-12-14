from django.core.management.base import BaseCommand, CommandError

from ... import Library
from ...build import build


class Command(BaseCommand):
    help = "Build the javascript and css for a/all apps."

    def add_arguments(self, parser):
        parser.add_argument(
            "app_libraries",
            nargs="*",
            help="'app_name' or 'app_name.library_name' of an application/library_name to build css/js for.",
        )

    def handle(self, *args, **options):
        libs_to_build = []
        app_libraries = options["app_libraries"]
        libraries = Library.registry
        if app_libraries:
            for app_library in app_libraries:
                if "." in app_library:
                    app_label, library_name = app_library.split(".", 1)
                    try:
                        libs_to_build.append(libraries[app_label][library_name])
                    except KeyError:
                        raise CommandError(f'Library "{app_library}" not found.')
                else:
                    if app_library in libraries:
                        libs_to_build.extend(libraries[app_library].values())
                    else:
                        raise CommandError(f'App "{app_library}" not found.')
        else:
            for app_libs in libraries.values():
                for lib in app_libs.values():
                    libs_to_build.append(lib)

        build(libs_to_build)
