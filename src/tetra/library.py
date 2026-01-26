import logging
import os
import shutil
import subprocess
import json
import warnings
from collections import defaultdict
from typing import Self

from django.apps import AppConfig, apps
from django.templatetags.static import static
from django.utils.functional import cached_property

from .conf import get_setting, get_esbuild_path
from .components.base import ComponentMetaClass, BasicComponent, Component
from .exceptions import LibraryError
from .utils import camel_case_to_underscore

logger = logging.getLogger(__name__)


class Library:
    # a dictionary to store all Library instances: [app_label][library][components]
    registry: defaultdict[str, dict[str, Self]] = defaultdict(dict)

    @staticmethod
    def __new__(
        cls, name: str = "", app: AppConfig | str = None, path: str = ""
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
            self.components: dict[str, type[BasicComponent] | ComponentMetaClass] = {}
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
        """Returns the filename of the compiled app/library-wide JavaScript file."""
        return f"{self.app.label}_{self.name}.js"

    @property
    def styles_filename(self):
        """Returns the filename of the compiled app/library-wide CSS file."""
        return f"{self.app.label}_{self.name}.css"

    @property
    def js_path(self):
        """Returns the path to the compiled app/library-wide JavaScript file."""
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
        """Returns the static URL of the library's compiled JavaScript file."""
        with open(f"{self.js_path}.filename") as f:
            js_filename = f.read()
        return static(os.path.join(self.app.label, "tetra", self.name, js_filename))

    @cached_property
    def styles_url(self):
        """Returns the static URL of the library's compiled CSS file."""
        with open(f"{self.styles_path}.filename") as f:
            styles_filename = f.read()
        return static(os.path.join(self.app.label, "tetra", self.name, styles_filename))

    def register(
        self,
        component_cls: type[BasicComponent] | type[Component],
        name: str | None = None,
    ):
        if not name:
            name = component_cls.__name__
        underscore_name = camel_case_to_underscore(name)

        def dec(cls: type[BasicComponent]):
            if hasattr(cls, "_library") and cls._library:
                if cls._library is not self:
                    # If this is a subclass of an already registered component,
                    # we need to make sure we don't just inherit the library
                    # and name.
                    if (
                        cls.__name__ == component_cls.__name__
                        and cls.__module__ == component_cls.__module__
                    ):
                        # This IS the same class, check if it was registered to a different library
                        if cls._library is not self:
                            raise LibraryError(
                                f"Error registering component '{component_cls.__name__}' to "
                                f"library {self.display_name}, as it is "
                                f"already registered to library {cls._library.display_name}."
                            )
                    else:
                        # This is a subclass, we can register it to a new library
                        pass
                else:
                    logger.warning(
                        f"The app {self.app} is trying to register the "
                        f"'{component_cls.__name__}' component, which is already "
                        f"registered to library {cls._library}. "
                        f"Ignoring second registration."
                    )
                    return cls
            component_cls._library = self
            component_cls._name = underscore_name
            self.components[underscore_name] = component_cls
            return cls

        def component_tag_compile_function(parser, token):
            # Modify token to include the "component" prefix
            tag = token.contents.split()[0]
            if tag == "@":
                warnings.warn(
                    "Use 'component' instead of '@' for component tags.",
                    DeprecationWarning,
                )
            # TODO: check if component with this name exists!
            if tag != "component":
                token.contents = (
                    f"component {tag} {' '.join(token.contents.split()[1:])}"
                )
            return do_component(parser, token)

        if component_cls:
            # Dynamically register a template tag with ComponentName and
            # library.ComponentName

            # Set the name and other attributes
            component_tag_compile_function.__name__ = name
            from .templatetags.tetra import do_component, register as tetra_register

            # Register the tag with Django's template system
            tetra_register.tag(
                name=name, compile_function=component_tag_compile_function
            )
            tetra_register.tag(
                name=f"{self.name}.{name}",
                compile_function=component_tag_compile_function,
            )

            return dec(component_cls)
        else:
            return dec

    def __contains__(self, component_name: str) -> bool:
        """Check if the library contains the given component name."""
        return component_name in self.components

    def build(self, force=False):
        library_cache_path = os.path.join(
            self.app.path, get_setting("TETRA_FILE_CACHE_DIR_NAME"), self.name
        )
        file_out_path = os.path.join(
            self.app.path, "static", self.app.label, "tetra", self.name
        )
        meta_path = os.path.join(library_cache_path, "build_meta.json")

        # Get current state of source files
        current_state = {}
        for component_name, component_cls in self.components.items():
            py_filename, _, _ = component_cls.get_source_location()
            if py_filename and os.path.exists(py_filename):
                current_state[py_filename] = os.path.getmtime(py_filename)

            for ext in ["js", "css"]:
                ext_path = component_cls._get_component_file_path_with_extension(ext)
                if ext_path and os.path.exists(ext_path):
                    current_state[ext_path] = os.path.getmtime(ext_path)

        # Check if we can skip build
        if not force and os.path.exists(meta_path) and os.path.exists(file_out_path):
            try:
                with open(meta_path, "r") as f:
                    saved_state = json.load(f)
                if saved_state == current_state:
                    # Check if expected output files exist
                    js_filename_path = f"{self.js_path}.filename"
                    styles_filename_path = f"{self.styles_path}.filename"

                    has_js = any(c.has_script() for c in self.components.values())
                    has_styles = any(c.has_styles() for c in self.components.values())

                    js_ok = not has_js or (
                        os.path.exists(js_filename_path)
                        and os.path.exists(
                            os.path.join(
                                file_out_path, open(js_filename_path).read().strip()
                            )
                        )
                    )
                    styles_ok = not has_styles or (
                        os.path.exists(styles_filename_path)
                        and os.path.exists(
                            os.path.join(
                                file_out_path, open(styles_filename_path).read().strip()
                            )
                        )
                    )

                    if js_ok and styles_ok:
                        return
            except Exception as e:
                print(f"Incremental build check failed: {e}")

        print(f"# Building {self.display_name}")

        # Clear existing files to prevent old versions
        if os.path.exists(file_out_path):
            shutil.rmtree(file_out_path)
        os.makedirs(file_out_path)

        # Also clear from STATIC_ROOT if it exists
        static_root = get_setting("STATIC_ROOT")
        if static_root:
            static_root_path = os.path.join(
                static_root, self.app.label, "tetra", self.name
            )
            if os.path.exists(static_root_path):
                shutil.rmtree(static_root_path)

        if os.path.exists(library_cache_path):
            # We don't rmtree the whole cache path because it might contain build_meta.json
            for item in os.listdir(library_cache_path):
                if item == "build_meta.json":
                    continue
                item_path = os.path.join(library_cache_path, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        else:
            os.makedirs(library_cache_path)

        self.build_js(library_cache_path, file_out_path)
        self.build_styles(library_cache_path, file_out_path)

        # Save current state
        with open(meta_path, "w") as f:
            json.dump(current_state, f)

    def build_js(self, library_cache_path, target_path):
        main_imports = []
        main_scripts = []
        # files_to_remove = []
        out_file_path = os.path.join(library_cache_path, self.js_filename)
        meta_filename = f"{self.js_filename}__meta.json"
        meta_file_path = os.path.join(library_cache_path, meta_filename)

        try:
            for component_name, component_cls in self.components.items():
                print(f" - {component_name}")
                if component_cls.has_script():
                    script = component_cls.extract_script()
                    py_filename, _, _ = component_cls.get_source_location()
                    py_dir = os.path.dirname(py_filename)
                    if component_cls._is_script_inline():
                        filename = os.path.join(
                            library_cache_path,
                            f"{os.path.basename(py_filename)}__{component_name}.tmp.js",
                        )
                        with open(filename, "w") as f:
                            f.write(script)
                        # files_to_remove.append(filename)
                    else:
                        filename = os.path.join(py_dir, f"{component_name}.js")
                    rel_path = os.path.relpath(filename, library_cache_path)
                    if os.name == "nt":
                        rel_path = rel_path.replace(os.sep, "/")
                    if not rel_path.startswith("./") and not rel_path.startswith("../"):
                        rel_path = "./" + rel_path
                    main_imports.append(f'import {component_name} from "{rel_path}";')
                    main_scripts.append(component_cls.render_script(component_name))
                else:
                    main_scripts.append(component_cls.render_script())

            with open(out_file_path, "w") as f:
                f.write("\n".join(main_imports))
                f.write("\n\n")
                f.write("\n".join(main_scripts))

            esbuild_ret = subprocess.run(
                [get_esbuild_path(), out_file_path]
                + get_setting("TETRA_ESBUILD_JS_ARGS")
                + [f"--outdir={target_path}", f"--metafile={meta_file_path}"]
            )

            if esbuild_ret.returncode != 0:
                print("ERROR BUILDING JS:", self.display_name)
                return
        finally:
            # for path in files_to_remove:
            #     os.remove(path)
            pass

        with open(meta_file_path) as f:
            meta = json.load(f)
        for path, data in meta["outputs"].items():
            if data.get("entryPoint", None):
                out_path = path
                break

        with open(f"{self.js_path}.filename", "w") as f:
            f.write(os.path.basename(out_path))

    def build_styles(self, library_cache_path, target_path):
        main_imports = []
        files_to_remove = []
        out_file_path = os.path.join(library_cache_path, self.styles_filename)
        meta_filename = f"{self.styles_filename}__meta.json"
        meta_file_path = os.path.join(library_cache_path, meta_filename)

        try:
            for component_name, component_cls in self.components.items():
                if component_cls.has_styles():
                    print(f" - {component_name}")
                    styles = component_cls.extract_styles()
                    py_filename, _, _ = component_cls.get_source_location()
                    py_dir = os.path.dirname(py_filename)
                    if component_cls._is_styles_inline():
                        filename = os.path.join(
                            library_cache_path,
                            f"{os.path.basename(py_filename)}__"
                            f"{component_name}.tmp.css",
                        )
                        with open(filename, "w") as f:
                            f.write(styles)
                        # files_to_remove.append(filename)
                    else:
                        filename = os.path.join(py_dir, f"{component_name}.css")
                    rel_path = os.path.relpath(filename, library_cache_path)
                    if os.name == "nt":
                        rel_path = rel_path.replace(os.sep, "/")
                    main_imports.append(f"@import '{rel_path}';")

            with open(out_file_path, "w") as f:
                f.write("\n".join(main_imports))

            esbuild_ret = subprocess.run(
                [get_esbuild_path(), out_file_path]
                + get_setting("TETRA_ESBUILD_CSS_ARGS")
                + [
                    f"--outdir={target_path}",
                    # These three lines below are a work around so that urls to images
                    # update correctly.
                    "--metafile=meta.json",
                    f"--outbase={self.app.path}",
                    f"--asset-names={os.path.relpath(self.app.path, target_path)}/[dir]/[name]",
                    "--allow-overwrite",
                    f"--metafile={meta_file_path}",
                ]
            )

            if esbuild_ret.returncode != 0:
                print("ERROR BUILDING CSS:", self.display_name)
                return
        finally:
            for path in files_to_remove:
                os.remove(path)

        with open(meta_file_path) as f:
            meta = json.load(f)
        for path, data in meta["outputs"].items():
            if data.get("entryPoint", None):
                out_path = path
                break

        with open(f"{self.styles_path}.filename", "w") as f:
            f.write(os.path.basename(out_path))
