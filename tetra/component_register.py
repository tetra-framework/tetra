import logging
import os
import pkgutil

from django.apps import apps
import importlib
from django.template import Template
import inspect
from collections import defaultdict

from .components.base import InlineTemplate, Component, BasicComponent
from .exceptions import ComponentError, ComponentNotFound
from .library import Library
from .utils import (
    camel_case_to_underscore,
    underscore_to_pascal_case,
    unsupported_modules,
    is_abstract,
)

logger = logging.getLogger(__name__)

find_libraries_done = False

# TODO: put that in a more global scope
components_module_names = ["components", "tetra_components"]


def find_component_libraries():
    """Finds libraries in component modules of all installed django apps."""
    global find_libraries_done
    if find_libraries_done:
        return
    importlib.invalidate_caches()
    for components_module_name in components_module_names:
        for app_config in [
            a
            for a in apps.get_app_configs()
            if a.module.__name__ not in unsupported_modules
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
                    # if library name is already registered, get the instance, else register it.
                    library = Library(name=library_name, app=app_config)

                    # if submodule is a package, treat it as library package
                    library_module_name = ".".join(
                        [app_config.name, components_module_name, library_name]
                    )
                    try:
                        library_module = importlib.import_module(library_module_name)
                    except ModuleNotFoundError as e:
                        # logger.critical(e)
                        raise ModuleNotFoundError(
                            f"Could not import library module '{library_module_name}': {e}"
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
                            == library_module_name
                            and not is_abstract(member)
                        ):
                            member._is_directory_component = False
                            library.register(member, name)

                    # if library is a package, search for component packages within
                    # library
                    if ispkg:
                        for component_info in pkgutil.iter_modules([library.path]):
                            components_found = 0
                            component_name = ".".join(
                                [library_module_name, component_info.name]
                            )
                            try:
                                component_module = importlib.import_module(
                                    component_name
                                )
                            except ModuleNotFoundError as e:
                                # logger.critical(e)
                                raise ModuleNotFoundError(
                                    f"Could not import module '{component_name}': {e}"
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
                                    and not is_abstract(member)
                                ):
                                    components_found += 1
                                    if components_found > 1:
                                        raise ComponentError(
                                            f"Multiple components found "
                                            f"in '{component_module.__name__}' in app '{app_config.label}'."
                                            f"This is not supported"
                                        )
                                    member._is_directory_component = True
                                    library.register(member, name)

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
    dynamic = False
    name_parts = name.split(".")
    error_message = ""
    if name.startswith("="):
        dynamic = True
        name_parts[0] = name_parts[0][1:]

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
        try:
            if len(name_parts) > 2:
                raise ComponentNotFound(
                    f'Component name "{name}" invalid, should be in form '
                    '"[library_name.]ComponentName".'
                )
            if len(name_parts) == 1:
                name_parts = ("default", name_parts[0])

            # Full component name, easy: <library>.<component>!
            for app_name in Library.registry:
                try:
                    if name_parts[0] in Library.registry[app_name]:
                        # return the first matching library that contains the component
                        return Library.registry[app_name][name_parts[0]].components[
                            camel_case_to_underscore(name_parts[1])
                        ]
                except KeyError:
                    continue
            else:
                raise ComponentNotFound(
                    f"Component '{name_parts[1]}' not found in library '{name_parts[0]}'."
                )

        except ComponentNotFound as e:
            error_message = str(e)

    # if no method lead to finding a component successfully, give the user a hint
    # which components are available.
    components = []
    for app_name, lib in Library.registry.items():
        if lib:
            for lib_name, library in lib.items():
                if library.components:
                    for component_name in library.components:
                        ln = f"{lib_name}." if lib_name != "default" else ""
                        components.append(
                            f"{ln}{underscore_to_pascal_case(component_name)}"
                        )
    if not error_message:
        error_message = f'Component "{name}" not found.'
    error_message += f"\nAvailable components are: {components}"

    raise ComponentNotFound(error_message)
