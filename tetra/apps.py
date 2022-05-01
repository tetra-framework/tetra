from pickle import NONE
from django.apps import AppConfig
from pathlib import Path
from .templates import monkey_patch_template


monkey_patch_template()


class TetraConfig(AppConfig):
    name = "tetra"

    def ready(self):
        from .component_register import find_component_libraries
        from . import default_settings
        from django.conf import settings

        for name in dir(default_settings):
            if name.isupper() and not hasattr(settings, name):
                setattr(settings, name, getattr(default_settings, name))

        if not hasattr(settings, "TETRA_ESBUILD_PATH"):
            if settings.BASE_DIR:
                setattr(
                    settings,
                    "TETRA_ESBUILD_PATH",
                    Path(settings.BASE_DIR) / "node_modules" / ".bin" / "esbuild",
                )
            else:
                setattr(settings, "TETRA_ESBUILD_PATH", None)

        find_component_libraries()
