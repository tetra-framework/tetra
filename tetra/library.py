import logging
import os
import shutil
import subprocess
import json
from collections import defaultdict
from typing import Self

from django.apps import AppConfig, apps
from django.conf import settings
from django.templatetags.static import static
from django.utils.functional import cached_property

from .components.base import BasicComponentMetaClass
from .exceptions import LibraryError
from .utils import camel_case_to_underscore

logger = logging.getLogger(__name__)


class Library:
    registry = defaultdict(dict)

    @staticmethod
    def __new__(
        cls, name: str = None, app: AppConfig | str = None, path: str = ""
    ) -> Self:
        """Returns a new instance of Library, or the existing instance, if a library
        with the same app/name already exists."""

        if not name or not app:
            raise ValueError("Library 'name' and 'app' parameters are required.")
        if type(app) is str:
            app = apps.get_app_config(app)
        if app.label not in cls.registry or name not in cls.registry[app.label]:
            instance = super().__new__(cls)
            cls.registry[app.label][name] = instance
        else:
            instance = cls.registry[app.label][name]
        return instance

    def __init__(self, name: str, app: AppConfig | str, path: str = ""):
        if type(app) is str:
            app = apps.get_app_config(app)

        # Initialize only if this is a new instance
        if not hasattr(self, "components"):
            self.components = {}
            self.name = name
            self.path = path
            self.app: AppConfig = app

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Library: {self.display_name}>"

    @property
    def display_name(self):
        return f"{getattr(self, 'app').label}.{getattr(self, 'name')}"

    @property
    def js_filename(self):
        return f"{self.app.label}_{self.name}.js"

    @property
    def styles_filename(self):
        return f"{self.app.label}_{self.name}.css"

    @property
    def js_path(self):
        return os.path.join(
            self.app.path,
            "static",
            self.app.label,
            "tetra",
            self.name,
            self.js_filename,
        )

    @property
    def styles_path(self):
        return os.path.join(
            self.app.path,
            "static",
            self.app.label,
            "tetra",
            self.name,
            self.styles_filename,
        )

    @cached_property
    def js_url(self):
        with open(f"{self.js_path}.filename") as f:
            js_filename = f.read()
        return static(os.path.join(self.app.label, "tetra", self.name, js_filename))

    @cached_property
    def styles_url(self):
        with open(f"{self.styles_path}.filename") as f:
            styles_filename = f.read()
        return static(os.path.join(self.app.label, "tetra", self.name, styles_filename))

    def register(self, component: BasicComponentMetaClass = None, name=None):
        if not name:
            name = camel_case_to_underscore(component.__name__)

        def dec(cls: BasicComponentMetaClass):
            if hasattr(cls, "_library") and cls._library:
                if cls._library is not self:
                    raise LibraryError(
                        f"Error registering component '{component.__name__}' to "
                        f"library {self.display_name}, at it is "
                        f"already registered to library {cls._library.display_name}."
                    )
                else:
                    logger.warning(
                        f"Component {component.__name__} is already "
                        f"registered to library {cls._library}."
                        f"Ignoring second registration."
                    )
                    return cls
            component._library = self
            component._name = name
            self.components[name] = component
            return cls

        if component:
            return dec(component)
        else:
            return dec

    def __contains__(self, component_name: str) -> bool:
        """Check if the library contains the given component name."""
        return component_name in self.components

    def build(self):
        # TODO: check if source has changed and only build if it has
        print(f"# Building {self.display_name}")
        file_cache_path = os.path.join(
            self.app.path, settings.TETRA_FILE_CACHE_DIR_NAME, self.name
        )
        file_out_path = os.path.join(
            self.app.path, "static", self.app.label, "tetra", self.name
        )
        if os.path.exists(file_cache_path):
            shutil.rmtree(file_cache_path)
        os.makedirs(file_cache_path)
        if os.path.exists(file_out_path):
            shutil.rmtree(file_out_path)
        os.makedirs(file_out_path)
        self.build_js(file_cache_path, file_out_path)
        self.build_styles(file_cache_path, file_out_path)

    def build_js(self, file_cache_path, file_out_path):
        main_imports = []
        main_scripts = []
        files_to_remove = []
        main_path = os.path.join(file_cache_path, self.js_filename)
        meta_filename = f"{self.js_filename}__meta.json"
        meta_path = os.path.join(file_cache_path, meta_filename)

        try:
            for component_name, component in self.components.items():
                print(f" - {component_name}")
                if component.has_script():
                    script, is_inline = component.make_script_file()
                    py_filename, _, _ = component.get_source_location()
                    py_dir = os.path.dirname(py_filename)
                    if is_inline:
                        filename = (
                            f"{os.path.basename(py_filename)}__{component_name}.js"
                        )
                    else:
                        filename = f"{component_name}.js"
                    component_path = os.path.join(py_dir, filename)
                    files_to_remove.append(component_path)
                    with open(component_path, "w") as f:
                        f.write(script)
                    rel_path = os.path.relpath(component_path, file_cache_path)
                    if os.name == "nt":
                        rel_path = rel_path.replace(os.sep, "/")
                    main_imports.append(f'import {component_name} from "{rel_path}";')
                    main_scripts.append(component.make_script(component_name))
                else:
                    main_scripts.append(component.make_script())

            with open(main_path, "w") as f:
                f.write("\n".join(main_imports))
                f.write("\n\n")
                f.write("\n".join(main_scripts))

            esbuild_ret = subprocess.run(
                [settings.TETRA_ESBUILD_PATH, main_path]
                + settings.TETRA_ESBUILD_JS_ARGS
                + [f"--outdir={file_out_path}", f"--metafile={meta_path}"]
            )

            if esbuild_ret.returncode != 0:
                print("ERROR BUILDING JS:", self.display_name)
                return
        finally:
            for path in files_to_remove:
                os.remove(path)

        with open(meta_path) as f:
            meta = json.load(f)
        for path, data in meta["outputs"].items():
            if data.get("entryPoint", None):
                out_path = path
                break

        with open(f"{self.js_path}.filename", "w") as f:
            f.write(os.path.basename(out_path))

    def build_styles(self, file_cache_path, file_out_path):
        main_imports = []
        files_to_remove = []
        main_path = os.path.join(file_cache_path, self.styles_filename)
        meta_filename = f"{self.styles_filename}__meta.json"
        meta_path = os.path.join(file_cache_path, meta_filename)

        try:
            for component_name, component in self.components.items():
                if component.has_styles():
                    print(f" - {component_name}")
                    styles, is_inline = component.make_styles_file()
                    py_filename, _, _ = component.get_source_location()
                    py_dir = os.path.dirname(py_filename)
                    if is_inline:
                        filename = (
                            f"{os.path.basename(py_filename)}__{component_name}.css"
                        )
                    else:
                        filename = f"{component_name}.css"
                    component_path = os.path.join(py_dir, filename)
                    files_to_remove.append(component_path)
                    with open(component_path, "w") as f:
                        f.write(styles)
                    rel_path = os.path.relpath(component_path, file_cache_path)
                    if os.name == "nt":
                        rel_path = rel_path.replace(os.sep, "/")
                    main_imports.append(f"@import '{rel_path}';")

            with open(main_path, "w") as f:
                f.write("\n".join(main_imports))

            esbuild_ret = subprocess.run(
                [settings.TETRA_ESBUILD_PATH, main_path]
                + settings.TETRA_ESBUILD_CSS_ARGS
                + [
                    f"--outdir={file_out_path}",
                    # These three lines below are a work around so that urls to images
                    # update correctly.
                    "--metafile=meta.json",
                    f"--outbase={self.app.path}",
                    f"--asset-names={os.path.relpath(self.app.path, file_out_path)}/[dir]/[name]",
                    "--allow-overwrite",
                    f"--metafile={meta_path}",
                ]
            )

            if esbuild_ret.returncode != 0:
                print("ERROR BUILDING CSS:", self.display_name)
                return
        finally:
            for path in files_to_remove:
                os.remove(path)

        with open(meta_path) as f:
            meta = json.load(f)
        for path, data in meta["outputs"].items():
            if data.get("entryPoint", None):
                out_path = path
                break

        with open(f"{self.styles_path}.filename", "w") as f:
            f.write(os.path.basename(out_path))
