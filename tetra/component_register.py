import logging
import os
import pkgutil

from django.apps import apps
import importlib
from django.template import Template
import inspect
from collections import defaultdict

from .components.base import InlineTemplate, ComponentNotFound, Component
from .library import Library, ComponentLibraryException

logger = logging.getLogger(__file__)

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
        for app in apps.get_app_configs():
            if app.module.__name__ != "tetra":
                module_name = f"{app.module.__name__}.{components_module_name}"
                try:
                    components_module = importlib.import_module(module_name)
                    for name, member in inspect.getmembers(components_module):
                        if isinstance(member, Library):
                            if name in libraries[app.label]:
                                raise ComponentLibraryException(
                                    f'Library named "{name}" already in app "{app.label}".'
                                )
                            libraries[app.label][name] = member
                            member.name = name
                            member.app = app
                    # iter over a list of submodules in the
                    # components/tetra_components directory
                    for library_info in pkgutil.iter_modules(
                        components_module.__path__
                    ):
                        # if submodule is a package, it must be a library
                        if library_info.ispkg:
                            # import module dynamically and load it as library
                            # library_dotted_path = ".".join(
                            #     [
                            #         app.module.__name__,
                            #         components_module_name,
                            #         library_module_info.name,
                            #     ]
                            # )
                            try:
                                # module = importlib.import_module(component_dotted_path)

                                # check if library name is already registered.
                                library = libraries[app.label].get(library_info.name)
                                if not library:
                                    library = Library()
                                    # save library in a dictionary for later usage.
                                    libraries[app.label][library_info.name] = library
                                    library.name = library_info.name
                                    library.app = app

                                library_module = importlib.import_module(
                                    ".".join(
                                        [
                                            app.label,
                                            components_module_name,
                                            library_info.name,
                                        ]
                                    )
                                )
                                library_path = os.path.join(
                                    library_info.module_finder.path,
                                    library_info.name,
                                )

                                # search for component packages within library
                                for component_info in pkgutil.iter_modules(
                                    [library_path]
                                ):
                                    component_name = (
                                        f"{app.label}."
                                        f"{components_module_name}."
                                        f"{library.name}.{component_info.name}"
                                    )
                                    component_module = importlib.import_module(
                                        component_name
                                    )

                                    for name, member in inspect.getmembers(
                                        component_module, inspect.isclass
                                    ):
                                        if (
                                            issubclass(member, Component)
                                            and member is not Component
                                        ):
                                            library.register(member, name)

                            except ModuleNotFoundError as e:
                                pass
                        else:
                            # TODO: library is a file, register all components in it
                            #  automatically.
                            pass

                except ModuleNotFoundError as e:
                    # only raise the exception if the import raises secondary import errors.
                    # E.g. if the component imports a module that is non-existent.
                    if e.name != module_name:
                        raise e

                    # if the module just is not present, just ignore it - this just means
                    # that this app does not have a "components" package, which is ok.

    find_libraries_done = True


def resolve_component(context, name):
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
