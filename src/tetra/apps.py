from glob import glob
from django.apps import AppConfig
from pathlib import Path
import os

from . import Library
from .templates import monkey_patch_template
from django.utils.autoreload import autoreload_started

monkey_patch_template()


def watch_extra_files(sender, *args, **kwargs):
    watch = sender.extra_files.add
    for app_name, library in Library.registry.items():
        for lib_name, library_info in library.items():
            if library_info and library_info.path:
                # watch for html, js, and css files
                watch_list = glob(f"{library_info.path}/**/*.*", recursive=True)
                for file in watch_list:
                    if os.path.exists(file) and file.endswith((".html", ".css", ".js")):
                        watch(Path(file))


class TetraConfig(AppConfig):
    name = "tetra"

    def ready(self):
        from .component_register import find_component_libraries
        from tetra import checks  # noqa
        from .library import Library
        from .components.default.redirect import Redirect
        from .components.default.link import Link
        from .components.default.router import Router

        # Register router components in the default library
        # default_lib = Library("default", "tetra")
        #
        # # Set the library path so component resources can be discovered
        # default_lib.path = os.path.join(
        #     os.path.dirname(__file__), "components", "default"
        # )
        #
        # # Set _is_directory_component for Router so its JS file can be discovered
        # Router._is_directory_component = True
        # default_lib.register(Router)
        #
        # default_lib.register(Link)
        # default_lib.register(Redirect)

        find_component_libraries()
        autoreload_started.connect(watch_extra_files)
