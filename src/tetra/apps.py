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
            if library_info:
                # watch for html, js, and css files
                watch_list = glob(f"{library_info.path}/**/*.*", recursive=True)
                for file in watch_list:
                    if os.path.exists(file) and file.endswith((".html", ".css", ".js")):
                        watch(Path(file))


class TetraConfig(AppConfig):
    name = "tetra"

    def ready(self):
        from .component_register import find_component_libraries
        from tetra import default_settings, checks  # noqa
        from django.conf import settings

        for name in dir(default_settings):
            if name.isupper() and not hasattr(settings, name):
                setattr(settings, name, getattr(default_settings, name))

        if not hasattr(settings, "TETRA_ESBUILD_PATH"):
            bin_name = "esbuild"
            if os.name == "nt":
                bin_name = "esbuild.cmd"
            if settings.BASE_DIR:
                setattr(
                    settings,
                    "TETRA_ESBUILD_PATH",
                    Path(settings.BASE_DIR) / "node_modules" / ".bin" / bin_name,
                )
            else:
                setattr(settings, "TETRA_ESBUILD_PATH", None)

        find_component_libraries()
        autoreload_started.connect(watch_extra_files)
