import logging
import os
import pkgutil

from django.apps import apps
import importlib
from django.template import Template
import inspect
from collections import defaultdict

from .components.base import InlineTemplate, ComponentNotFound, Component, \
    BasicComponent, ComponentError
from .library import Library
from .utils import camel_case_to_underscore, underscore_to_pascal_case

logger = logging.getLogger(__name__)

libraries = defaultdict(dict)
find_libraries_done = False

# TODO: put that in a more global scope
components_module_names = ["components", "tetra_components"]


def find_component_libraries():
    """Finds libraries in component modules of all installed django apps."""
    global libraries
    global find_libraries_done
    if find_libraries_done:
        return
    importlib.invalidate_caches()
    for components_module_name in components_module_names:
        for app_config in [
            a for a in apps.get_app_configs() if a.module.__name__ != "tetra"
        ]:
            # from django.utils.module_loading import *

            module_name = f"{app_config.name}.{components_module_name}"
            try:
                components_module = importlib.import_module(module_name)

                # iter over a list of submodules in the
                # components directory
                for module_finder, library_name, ispkg in pkgutil.iter_modules(
                    components_module.__path__
                ):
                    # check if library name is already registered, else register it.
                    library = libraries[app_config.label].get(library_name)
                    if not library:
                        library = Library(name=library_name, app=app_config)
                        # save library in a dictionary for later usage.
                        libraries[app_config.label][library_name] = library

                    # if submodule is a package, treat it as library package
                    try:
                        library_module = importlib.import_module(
                            ".".join(
                                [
                                    app_config.label,
                                    components_module_name,
                                    library_name,
                                ]
                            )
                        )

                        library.path = os.path.join(
                            module_finder.path,
                            library_name,
                        )

                        # Search for components directly defined in the library package.
                        # this could be in e.g. default.py or in default/__init__.py
                        for name, member in inspect.getmembers(
                            library_module, inspect.isclass
                        ):
                            # accept only BasicComponent subclasses, and ignore imports:
                            # only classes defined in that module are registered as
                            # components.
                            if (
                                issubclass(member, BasicComponent)
                                and getattr(member, "__module__", None)
                                == library_module.__name__
                            ):
                                library.register(member, camel_case_to_underscore(name))

                        # if library is a package, search for component packages within
                        # library
                        if ispkg:
                            components_found = 0
                            for component_info in pkgutil.iter_modules([library.path]):
                                component_name = ".".join(
                                    [
                                        app_config.label,
                                        components_module_name,
                                        library.name,
                                        component_info.name,
                                    ]
                                )
                                component_module = importlib.import_module(
                                    component_name
                                )
                                for name, member in inspect.getmembers(
                                    component_module, inspect.isclass
                                ):
                                    # accept only BasicComponent subclasses, and ignore imports:
                                    # only classes defined in that module are registered as
                                    # components.
                                    if (
                                        issubclass(member, BasicComponent)
                                        and getattr(member, "__module__", None)
                                        == component_module.__name__
                                    ):
                                        components_found += 1
                                        if components_found > 1:
                                            raise ComponentError(
                                                f"Multiple components found "
                                                f"in '{component_module.__name__}' in app '{app_config.label}'."
                                                f"This is not supported"
                                            )
                                        library.register(
                                            member, camel_case_to_underscore(name)
                                        )

                    except ModuleNotFoundError:
                        pass

                    # else:
                    #     # TODO: library is a file, register all components in it
                    #     #  automatically.
                    #     for name, member in inspect.getmembers(components_module):
                    #         if isinstance(member, Library):
                    #             if name in libraries[app_config.label]:
                    #                 raise ComponentLibraryException(
                    #                     f'Library named "{name}" already in app "{app_config.label}".'
                    #                 )
                    #             libraries[app_config.label][name] = member
                    #             member.name = name
                    #             member.app = app_config

            except ModuleNotFoundError as e:
                # only raise the exception if the import raises secondary import errors.
                # E.g. if the component imports a module that is non-existent.
                if e.name != module_name:
                    raise e

                # if the module just is not present, just ignore it - this just means
                # that this app does not have a "components" package, which is ok.

    find_libraries_done = True


def resolve_component(context, name: str) -> Component:
    """Takes a Django context and a component name, and returns the corresponding
    component instance.

    Attributes:
        context (RequestContext): The Django context in which the component is being rendered.
        name (str): The name of the component to resolve. This can be a full component name,
            or a dot-separated string representing a context variable containing a
            component.
        Returns:
            The resolved component instance.
    """
    template = context.template
    current_app = None
    dynamic = False
    if name.startswith("="):
        name = name[1:]
        dynamic = True
    name_parts = name.split(".")

    if dynamic:
        # traverse context
        value = context
        for key in name_parts:
            try:
                # try to get component as key from context dict
                value = value[key]
            except KeyError:
                raise ComponentNotFound(
                    f"Dynamic component '{name}' not found in context."
                )
            except TypeError:
                # then this name part is already an object.
                # try to read attribute from object
                value = getattr(value, key, None)
        if value is not None:
            logger.debug(f"Resolved dynamic component: '{name}' to {Component}")
            return value
    else:
        if len(name_parts) == 3:
            # Full component name, easy!
            try:
                return libraries[name_parts[0]][name_parts[1]].components[
                    camel_case_to_underscore(name_parts[2])
                ]
            except KeyError:
                ComponentNotFound(f'Component "{name}" not found.')

        if len(name_parts) > 3:
            raise ComponentNotFound(
                f'Component name "{name}" invalid, should be in form '
                '"[app_name.][library_name.]ComponentName".'
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

        elif (
            isinstance(template, Template) and template.origin and template.origin.name
        ):
            # It's a normal template from a file
            file_name = template.origin.name
            for app_conf in apps.get_app_configs():
                if file_name.startswith(app_conf.path):
                    current_app = app_conf

        if not current_app and len(name_parts) < 3:
            raise ComponentNotFound(
                f'Unable to ascertain current app and so component name "{name}" should be '
                'in full form "app_name.library_name.ComponentName".'
            )

        if current_app and len(name_parts) == 1:
            # Try in current apps default library
            try:
                return libraries[current_app.label]["default"].components[
                    camel_case_to_underscore(name_parts[0])
                ]
            except KeyError:
                pass

        if current_app and len(name_parts) == 2:
            # try other library name in current_app
            try:
                return libraries[current_app.label][name_parts[0]].components[
                    camel_case_to_underscore(name_parts[1])
                ]
            except KeyError:
                pass

        if len(name_parts) == 2:
            # try other part1.default.part2
            try:
                return libraries[name_parts[0]]["default"].components[
                    camel_case_to_underscore(name_parts[1])
                ]
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
                        components.append(
                            f"{app_name}.{lib_name}.{underscore_to_pascal_case(component_name)}"
                        )

    raise ComponentNotFound(
        f'Component "{name}" not found. Available components are: {components}'
    )
