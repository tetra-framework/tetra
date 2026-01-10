from pathlib import Path
from django.apps import apps
from django.template.loaders.filesystem import Loader as FileSystemLoader
from django.conf import settings
from tetra.constants import COMPONENT_MODULE_NAMES


class Loader(FileSystemLoader):
    """Loader that loads templates from "components" directories in INSTALLED_APPS packages."""

    # @functools.lru_cache
    def get_dirs(self):
        # Collect all `components` directories from each app
        component_dirs = []
        for app_config in apps.get_app_configs():
            if app_config.label != "tetra":
                # TODO use dynamic components_module_names
                components_dir = Path(app_config.path) / getattr(
                    settings, "TETRA_COMPONENTS_MODULE_NAMES", COMPONENT_MODULE_NAMES
                )
                if components_dir.is_dir():
                    component_dirs.append(components_dir)
        return component_dirs
