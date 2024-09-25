import logging

from django.apps import apps
from importlib import import_module
from django.template import Template
import inspect
from collections import defaultdict

from .components.base import InlineTemplate, ComponentNotFound, Component
from .library import Library, ComponentLibraryException

logger = logging.getLogger(__name__)

libraries = defaultdict(dict)
find_libraries_done = False

component_module_names = ["components", "tetra_components"]


def find_component_libraries():
    """Finds libraries in component modules of all installed django apps."""
    global libraries
    global find_libraries_done
    if find_libraries_done:
        return
    for component_module_name in component_module_names:
        for app in apps.get_app_configs():
            module_name = f"{app.module.__name__}.{component_module_name}"
            try:
                component_module = import_module(module_name)
                for name, member in inspect.getmembers(component_module):
                    if isinstance(member, Library):
                        if name in libraries[app.label]:
                            raise ComponentLibraryException(
                                f'Library named "{name}" already in app "{app.label}".'
                            )
                        libraries[app.label][name] = member
                        member.name = name
                        member.app = app
            except ModuleNotFoundError as e:
                # only raise the exception if the import raises secondary import errors.
                # E.g. if the component imports a module that is non-existent.
                if e.name != module_name:
                    raise e

                # if the module just is not present, just ignore it - this just means
                # that this app does not have a "components" package, which is ok.

    find_libraries_done = True


def resolve_component(context, name) -> Component:
    template = context.template
    current_app = None
    name_parts = name.split(".")

    if len(name_parts) == 3:
        # Full component name, easy!
        try:
            return libraries[name_parts[0]][name_parts[1]].components[name_parts[2]]
        except KeyError:
            ComponentNotFound(f'Component "{name}" not found.')

    if len(name_parts) > 3:
        raise ComponentNotFound(
            f'Component name "{name}" invalid, should be in form '
            '"[app_name.][library_name.]component_name".'
        )

    # if component is called with 2 parts, we need a current_app context to find the
    # component
    if (
        isinstance(template, InlineTemplate)
        and template.origin
        and hasattr(template.origin, "component")
    ):
        #  It's a template on a component
        module = inspect.getmodule(template.origin.component)
        module_name = module.__name__
        for app_conf in apps.get_app_configs():
            if module_name.startswith(app_conf.module.__name__):
                current_app = app_conf

    elif isinstance(template, Template) and template.origin and template.origin.name:
        # It's a normal template from a file
        file_name = template.origin.name
        for app_conf in apps.get_app_configs():
            if file_name.startswith(app_conf.path):
                current_app = app_conf

    if not current_app and len(name_parts) < 3:
        raise ComponentNotFound(
            f'Unable to ascertain current app and so component name "{name}" should be '
            'in full form "app_name.library_name.component_name".'
        )

    if current_app and len(name_parts) == 1:
        # Try in current apps default library
        try:
            return libraries[current_app.label]["default"].components[name_parts[0]]
        except KeyError:
            pass

    if current_app and len(name_parts) == 2:
        # try other library name in current_app
        try:
            return libraries[current_app.label][name_parts[0]].components[name_parts[1]]
        except KeyError:
            pass

    if len(name_parts) == 2:
        # try other part1.default.part2
        try:
            return libraries[name_parts[0]]["default"].components[name_parts[1]]
        except KeyError:
            pass

    # if no method lead to finding a component successfully, give the user a hint
    # which components are available.
    components = []
    for app_name, lib in libraries.items():
        if lib:
            for lib_name, library in lib.items():
                if library.components:
                    for component_name in library.components:
                        components.append(f"{app_name}.{lib_name}.{component_name}")

    raise ComponentNotFound(
        f'Component "{name}" not found. Available components are: {components}'
    )
