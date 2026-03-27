import hashlib
import logging
import importlib
import os
from datetime import datetime, date, time
from decimal import Decimal

from copy import copy
from typing import Optional, Self, Any, get_origin, get_args, Union
from types import FunctionType, NoneType, UnionType
from enum import Enum
import inspect
import re
import itertools
from weakref import WeakKeyDictionary
from functools import wraps
from threading import local

from django import forms
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db.models.fields.files import FieldFile
from django.db import models
from django.db.models import Model
from django.db.models.base import ModelBase
from django.forms import (
    Form,
    modelform_factory,
    BaseForm,
    FileField,
    ModelForm,
    ModelChoiceField,
)
from django.template.base import Template
from django.template.loader import render_to_string
from django.template import (
    RequestContext,
    TemplateSyntaxError,
    TemplateDoesNotExist,
    Engine,
)
from django.template.loader_tags import BLOCK_CONTEXT_KEY, BlockContext, BlockNode
from django.utils.safestring import mark_safe, SafeString
from django.utils.html import escapejs, escape
from django.utils.functional import SimpleLazyObject
from django.http import JsonResponse, HttpRequest, FileResponse, HttpResponse
from django.urls import reverse
from django.template.loaders.filesystem import Loader as FileSystemLoader
from django.db import models
from django.core.files.base import File
from django.contrib.messages import get_messages

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from ..exceptions import ComponentError, StaleComponentStateError
from ..middleware import TetraHttpRequest
from ..utils import (
    camel_case_to_underscore,
    to_json,
    TetraJSONEncoder,
    isclassmethod,
    param_names_exist,
    param_count,
    has_single_root,
    NamedTemporaryUploadedFile,
)
from ..types import ComponentData
from ..state import encode_component, decode_component
from ..templates import InlineOrigin, InlineTemplate

from .callbacks import CallbackList
from .utils import get_next_autokey, reset_autokey_count


thread_local = local()

logger = logging.getLogger(__name__)

# Types that should be preserved as-is during serialization
SERIALIZABLE_TYPES = (
    str,
    int,
    float,
    bool,
    list,
    dict,
    tuple,
    set,
    type(None),
    date,
    datetime,
    time,
    Decimal,
    Enum,
    File,
    models.Model,
)


def _has_own_attribute(cls, attr_name: str) -> bool:
    """Check if a class has its own attribute (not inherited from base classes).

    Args:
        cls: The class to check
        attr_name: The attribute name to look for

    Returns:
        True if the class defines the attribute itself with a non-empty value,
        False if inherited, not present, or empty
    """
    # First check if it's directly in the class's __dict__
    if attr_name in cls.__dict__:
        attr_value = cls.__dict__[attr_name]
        # Only return True if the value is non-empty (not None, not empty string)
        if attr_value:
            return True
        # If empty, continue to check parents
        return False

    # If not in __dict__, check if it exists and differs from all parents
    if hasattr(cls, attr_name):
        attr_value = getattr(cls, attr_name, None)
        if attr_value:  # Only check if not empty/None
            # Check if this is the same as any parent's attribute (inherited)
            for parent in cls.__mro__[1:]:
                if (
                    hasattr(parent, attr_name)
                    and getattr(parent, attr_name, None) == attr_value
                ):
                    # Found in parent with same value, so it's inherited
                    return False
            # Not found in parents with same value, so it's defined in this class
            return True
    return False


def make_template(cls) -> Template | None:
    """Create a template from a component class.

    Uses either the `cls.template` attribute as inline template string,
    or the html template file source in the component's directory. If both are defined,
    'template' overrides the file template.
    """
    from ..templatetags.tetra import get_nodes_by_type_deep

    def prepare_template_source(source):
        if re.match(r"^\s*{%\s*extends", source):
            # If the template starts with an extends tag, we must insert the
            # load tetra tag AFTER the extends tag.
            return re.sub(
                r"^(\s*{%\s*extends\s+['\"][^'\"]+['\"]\s*%})",
                r"\1{% load tetra %}",
                source,
            )
        return "{% load tetra %}" + source

    # Template resolution order:
    # 1. Inline template of THIS class
    # 2. External template file of THIS class
    # 3. Inherited template from parent class (either inline or external)

    # Check if template is defined inline in THIS class (not inherited)
    has_own_inline_template = _has_own_attribute(cls, "template")

    # 1. Use inline template if defined in THIS class
    if has_own_inline_template:
        if not cls.template:
            raise ComponentError(f"Component '{cls.__name__}' has an empty template.")
        making_lazy_after_exception = False
        filename, line = cls.get_template_source_location()
        origin = InlineOrigin(
            name=f"{filename}:{cls.__name__}.template",
            template_name=filename,
            start_line=line,
            component=cls,
        )
        try:
            template = InlineTemplate(
                prepare_template_source(cls.template),
                origin=origin,
            )
        except TemplateSyntaxError as e:
            # By default, we want to compile templates during python compile time.
            # However, the template exceptions are much better when raised at runtime
            # as it shows a nice stack trace in the browser. We therefore create a
            # "Lazy" template after a compile error that will run in the browser when
            # testing.
            from django.conf import settings

            logger.error(
                f"Failed to compile inline template for component '{cls.__name__}': {e}"
            )
            if settings.DEBUG:
                making_lazy_after_exception = True
                template = SimpleLazyObject(
                    lambda: InlineTemplate(
                        prepare_template_source(cls.template),
                        origin=origin,
                    )
                )
            else:
                raise ComponentError(
                    f"Template compilation failed for component '{cls.__name__}': {e}"
                )

        if not making_lazy_after_exception and template is not None:
            for i, block_node in enumerate(
                get_nodes_by_type_deep(template.nodelist, BlockNode)
            ):
                if not getattr(block_node, "origin", None):
                    block_node.origin = origin

    elif hasattr(cls, "template_name"):
        raise NotImplementedError(
            f"'template_name' is not implemented for Tetra components ({cls})"
        )

    # 2. Try to find external template file of THIS class
    else:
        module = importlib.import_module(cls.__module__)
        external_template_found = False

        # Check if this is a directory-style component with external template
        if hasattr(module, "__path__"):
            module_path = module.__path__[0]
            component_name = module.__name__.split(".")[-1]
            template_file_name = f"{component_name}.html"

            # Try to load the external template
            try:
                engine = Engine(dirs=[module_path], app_dirs=False)
                loader = FileSystemLoader(engine)
                for template_path in loader.get_template_sources(template_file_name):
                    try:
                        # Open and read the template source
                        with open(template_path.name, "r", encoding="utf-8") as f:
                            template_source = f.read()

                        origin = InlineOrigin(  # TODO: isn't that a normal Origin?
                            name=os.path.join(module_path, template_file_name),
                            template_name=template_file_name,
                            start_line=0,
                            component=cls,
                        )
                        # Compile the template
                        template = Template(
                            prepare_template_source(template_source),
                            origin,
                            template_file_name,
                        )
                        external_template_found = True
                        break
                    except FileNotFoundError:
                        # If the file is not found, continue with the next source
                        continue
            except TemplateDoesNotExist:
                # External template was not found, try inherited template in next step
                pass

        # 3. Fall back to inherited template from parent class
        if not external_template_found:
            # First check if parent has a compiled template
            parent_with_template = None
            for base in cls.__mro__[1:]:
                if hasattr(base, "_template"):
                    if base._template is not None:
                        # Use parent's compiled template
                        return base._template
                    else:
                        # Parent exists but template not compiled yet
                        # Remember this parent for later
                        parent_with_template = base

            # If parent has template but not compiled yet, return None
            # This will cause the calling code to defer compilation
            if parent_with_template is not None:
                return None

            # Otherwise check for inherited inline template
            has_inherited_template = (
                hasattr(cls, "template") and cls.template is not None
            )
            if has_inherited_template:
                # Use inherited template
                if not cls.template:
                    raise ComponentError(
                        f"Component '{cls.__name__}' has an empty template."
                    )
                making_lazy_after_exception = False
                filename, line = cls.get_template_source_location()
                origin = InlineOrigin(
                    name=f"{filename}:{cls.__name__}.template",
                    template_name=filename,
                    start_line=line,
                    component=cls,
                )
                try:
                    template = InlineTemplate(
                        prepare_template_source(cls.template),
                        origin=origin,
                    )
                except TemplateSyntaxError as e:
                    from django.conf import settings

                    logger.error(
                        f"Failed to compile inherited template for component '{cls.__name__}': {e}"
                    )
                    if settings.DEBUG:
                        making_lazy_after_exception = True
                        template = SimpleLazyObject(
                            lambda: InlineTemplate(
                                prepare_template_source(cls.template),
                                origin=origin,
                            )
                        )
                    else:
                        raise ComponentError(
                            f"Template compilation failed for component '{cls.__name__}': {e}"
                        )

                if not making_lazy_after_exception and template is not None:
                    for i, block_node in enumerate(
                        get_nodes_by_type_deep(template.nodelist, BlockNode)
                    ):
                        if not getattr(block_node, "origin", None):
                            block_node.origin = origin
            else:
                # No template found anywhere
                raise ComponentError(
                    f"'{cls.__module__}.{cls.__name__}' is not a valid component. "
                    f"You either have to put it into a correct library directory with a "
                    f"'{camel_case_to_underscore(cls.__name__)}.html' template file "
                    f"alongside, or add a 'template' attribute to the component."
                )
    if not re.match(r"^\s*{%\s*extends", template.source) and not has_single_root(
        template.source
    ):
        raise ComponentError(
            f"Component template '{cls.__name__}.template' must contain exactly "
            f"one top-level tag."
        )
    return template


class RenderDataMode(Enum):
    """The mode how to render the component's data."""

    INIT = 0  # initialize data. There was no component state before
    MAINTAIN = 1  # keep component data
    UPDATE = 2  # update component data with new data from server


class BaseRenderer:
    def __init__(self, component: "BasicComponent"):
        self.component = component

    def render(self, **kwargs) -> SafeString:
        self.component.recalculate_attrs(component_method_finished=True)
        context = self.component.get_context_data()

        with context.render_context.push_state(
            self.component._template, isolated_context=True
        ):
            if self.component._slots:
                if BLOCK_CONTEXT_KEY not in context.render_context:
                    context.render_context[BLOCK_CONTEXT_KEY] = BlockContext()
                block_context = context.render_context[BLOCK_CONTEXT_KEY]
                block_context.add_blocks(self.component._slots)

            if context.template is None:
                with context.bind_template(self.component._template):
                    html = self.component._template._render(context)
            else:
                html = self.component._template._render(context)

        return mark_safe(html)


class ComponentRenderer(BaseRenderer):
    def render(self, mode=RenderDataMode.INIT, **kwargs) -> SafeString:
        if hasattr(thread_local, "_tetra_render_mode"):
            mode = thread_local._tetra_render_mode
            set_thread_local = False
        else:
            thread_local._tetra_render_mode = mode
            set_thread_local = True

        html = super().render(**kwargs)

        if set_thread_local:
            del thread_local._tetra_render_mode

        tag_name = re.match(r"^\s*(<!--.*-->)?\s*<\w+", html)
        if not tag_name:
            if not re.match(r"^\s*{%\s*extends", self.component._template.source):
                raise ComponentError(
                    f"Error in {self.component.__class__.__name__}: The component's template is "
                    "not enclosed in HTML tags."
                )
            tag_name = re.search(r"<\w+", html)
            if not tag_name:
                raise ComponentError(
                    f"Error in {self.component.__class__.__name__}: The component's rendered "
                    "template is not enclosed in HTML tags."
                )

        tag_name_end = tag_name.end(0)
        extra_tags = self.component.get_extra_tags()

        if self.component.key:
            extra_tags.update({"key": self.component.key})

        if mode == RenderDataMode.UPDATE and self.component._is_resumed_from_state:
            data_json = escape(to_json(self.component._render_data()))
            old_data_json = escape(to_json(self.component._resumed_from_state_data))
            extra_tags.update({"x-data": ""})
            extra_tags.update({"x-data-update": data_json})
            extra_tags.update({"x-data-update-old": old_data_json})
        elif mode == RenderDataMode.MAINTAIN:
            extra_tags.update({"x-data": ""})
            extra_tags.update({"x-data-maintain": ""})
        else:
            data_json = escapejs(to_json(self.component._render_data()))
            extra_tags.update(
                {"x-data": f"{self.component.full_component_name()}('{data_json}')"}
            )

        for method_data in self.component._public_methods:
            if "event_subscriptions" in method_data:
                for event in method_data["event_subscriptions"]:
                    extra_tags.update(
                        {f"@{event}": f'{method_data["name"]}($event.detail)'}
                    )

        tags_strings = [f"{key}=\"{value or ''}\"" for key, value in extra_tags.items()]
        html = f'{html[:tag_name_end]} {" ".join(tags_strings)} {html[tag_name_end:]}'
        return mark_safe(html)


class BasicComponent:
    __abstract__ = True
    style: str = ""
    script: Optional[str] = None
    component_id: Optional[str] = None
    _is_resumed_from_state = False
    _is_directory_component: bool = False
    _template: Template
    _to_compile = []
    _name = None
    _library = None
    _app = None

    def __init_subclass__(cls, **kwargs):
        from tetra.state import loading_libraries

        super().__init_subclass__(**kwargs)
        cls._name = camel_case_to_underscore(cls.__name__)

        if "__abstract__" not in cls.__dict__ or cls.__dict__["__abstract__"] is False:
            if loading_libraries:
                # postpone template compiling to time when all libraries are loaded
                cls._to_compile.append(cls)
            else:
                cls._template = make_template(cls)
                # If template is None, it means parent template isn't ready yet
                # Add to compile list to compile later
                if cls._template is None:
                    cls._to_compile.append(cls)

    def __init__(
        self,
        _request: TetraHttpRequest | HttpRequest,
        _attrs: dict[str, Any] | None = None,
        _context: dict[str, Any] | RequestContext | None = None,
        _slots=None,
        key: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        """Initializes the component with the provided attributes and context.

        It calls load() with the optional args/kwargs."""

        super().__init__()  # call init without kwargs.
        self.request = _request
        self.attrs = _attrs or {}
        if key is not None:
            self.attrs["key"] = key

        if "key" not in self.attrs:
            self.attrs["key"] = get_next_autokey()

        self._context = _context or {}
        self._slots = _slots
        self.renderer = BaseRenderer(self)
        # FIXME: it could lead to mismatching component ids if it is recreated after
        #  page reloading - test this for channels/long-lasting websocket connections
        self.component_id = self.get_component_id()
        self._call_load(*args, **kwargs)

    @classmethod
    def _compile_all_templates(mcls):
        while mcls._to_compile:
            cls = mcls._to_compile.pop(0)
            # Check if class has its own external template file before inheriting
            # This allows subclasses to override inherited templates with external files
            module = importlib.import_module(cls.__module__)
            has_external_template = False
            if hasattr(module, "__path__"):
                module_path = module.__path__[0]
                component_name = module.__name__.split(".")[-1]
                template_file_path = os.path.join(module_path, f"{component_name}.html")
                has_external_template = os.path.exists(template_file_path)

            # Compile if: no _template yet, OR has external template (to override inherited)
            if "_template" not in cls.__dict__ or has_external_template:
                cls._template = make_template(cls)

    def get_component_id(self) -> str:
        """Creates a unique, reproducible, session-persistent component id.

        This is calculated from the component name, optionally the session key,
        and the component key, if available.
        """
        try:
            name = self.full_component_name()
        except ComponentError:
            name = f"{self.__class__.__module__}.{self.__class__.__name__}"

        session_key = (
            self.request.session.session_key if hasattr(self.request, "session") else ""
        )
        component_key = self.attrs.get("key", "")
        s = f"{name}{session_key}{component_key}"
        return hashlib.blake2b(s.encode(), digest_size=8).hexdigest()

    @classmethod
    def full_component_name(cls) -> str:
        if not cls._library:
            raise ComponentError(
                f"Component class '{cls.__name__}' is not registered in a library."
            )
        return f"{cls._library.app.label}__{cls._library.name}__{cls._name}"

    def get_extra_tags(self) -> dict[str, str | None]:
        """Returns extra tags to be included in the component's HTML.

        This method can be overridden in subclasses to add custom
        attributes or classes to the component's HTML. Don't forget to call
        super().get_extra_tags() in your own implementation.
        """
        return {"tetra-component-id": self.component_id}

    @classmethod
    def get_source_location(cls) -> tuple[str, int, int]:
        """Returns the filename, line number, and line count of the component's
        source code."""
        filename = inspect.getsourcefile(cls)
        if not filename:
            raise ComponentError(
                f"Could not find source file for component '{cls.__name__}'."
            )
        lines, start = inspect.getsourcelines(cls)
        return filename, start, len(lines)

    @classmethod
    def get_template_source_location(cls) -> tuple[str, int | None]:
        """Returns the filename and startline number of the component's template,
        if available."""
        filename, comp_start, com_end = cls.get_source_location()
        if not hasattr(cls, "template") or not cls.template:
            # this is a directory style component
            filename = cls._get_component_file_path_with_extension("html")
            return filename, 0
        with open(filename, "r") as f:
            source = f.read()
        try:
            start = source.index(cls.template)
        except ValueError:
            # If the template is not found exactly, it might be due to
            # indentation or other formatting changes if the component
            # was defined dynamically.
            return filename, comp_start
        line = source[:start].count("\n") + 1
        return filename, line

    @classmethod
    def _get_component_file_path_with_extension(cls, extension):
        if cls._is_directory_component is not True:
            # assume this is an inline component, no css/js files available
            return ""
        # Check if THIS class's module is actually a package (has __path__)
        # Don't rely on inherited _is_directory_component value
        module = importlib.import_module(cls.__module__)
        if not hasattr(module, "__path__"):
            # Not a directory component
            return ""
        component_name = module.__name__.split(".")[-1]
        module_path = module.__path__[0]
        file_name = f"{component_name}.{extension}"
        return os.path.join(module_path, file_name)

    @classmethod
    def _read_component_file_with_extension(cls, extension) -> str:
        file_path = cls._get_component_file_path_with_extension(extension)
        if not os.path.exists(file_path):
            return ""

        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            # handle al other errors as well: IOError, UnicodeDecodeError, OSError
            # FileNotFoundError is already handled by exists() above
            logger.critical(f"Error reading component file '{file_path}': {e}")
            return ""

    @classmethod
    def has_script(cls) -> bool:
        """Returns True if the component has a javascript script defined in the class or a file
        in the component directory.

        Follows discovery rules:
        1. Check current class for inline script (takes precedence)
        2. Check current class for external JS file
        3. Check base classes for inline script
        4. Check base classes for external JS file
        """
        # Check current class first (inline takes precedence)
        if _has_own_attribute(cls, "script"):
            return True
        # Check current class for external file
        js_file = cls._get_component_file_path_with_extension("js")
        if os.path.exists(js_file):
            return True
        # Check base classes
        for base in cls.__mro__[1:]:
            if hasattr(base, "has_script") and base is not BasicComponent:
                if base.has_script():
                    return True
        return False

    @classmethod
    def _is_script_inline(cls) -> bool:
        """Returns True if the component has inline JavaScript script.

        Follows discovery rules:
        1. Check current class for inline script (takes precedence)
        2. Check base classes for inline script
        """
        # Check current class first
        if _has_own_attribute(cls, "script"):
            return True
        # Check base classes
        for base in cls.__mro__[1:]:
            if hasattr(base, "_is_script_inline") and base is not BasicComponent:
                if base._is_script_inline():
                    return True
        return False

    @classmethod
    def extract_script(cls) -> str:
        """Returns the JavaScript code extracted from either inline or external sources.

        Follows discovery rules:
        1. If current class has inline script, use it
        2. If current class has external JS file, use it
        3. Check base classes with same rules

        Returns:
            The JavaScript code as a string
        """
        # Check current class for inline script (takes precedence)
        if _has_own_attribute(cls, "script"):
            source_filename, comp_start_line, source_len = cls.get_source_location()
            with open(source_filename, "r") as f:
                py_source = f.read()
            comp_start_offset = len("\n".join(py_source.split("\n")[:comp_start_line]))
            start = py_source.index(cls.script, comp_start_offset)
            before = py_source[:start]
            before = re.sub(r"\S", " ", before)
            return f"{before}{cls.script}"
        # Check current class for external file
        js_file = cls._get_component_file_path_with_extension("js")
        if os.path.exists(js_file):
            logger.debug(
                f"Found JavaScript file '{js_file}' for component '{cls.__name__}'"
            )
            return cls._read_component_file_with_extension("js")
        # Check base classes
        for base in cls.__mro__[1:]:
            if hasattr(base, "extract_script") and base is not BasicComponent:
                script = base.extract_script()
                if script:
                    logger.debug(
                        f"Found script from base class '{base.__name__}' for component '{cls.__name__}'"
                    )
                    return script
        logger.debug(f"No JavaScript file for component '{cls.__name__}'")
        return ""

    @classmethod
    def render_script(cls, component_var=None) -> str:
        """Returns the raw JavaScript code for BasicComponent.

        Unlike Component, BasicComponent returns raw JS without Alpine.js component registration.
        This allows BasicComponents to include utility scripts in the bundle without the overhead
        of full component state management.
        """
        if component_var:
            return component_var
        elif cls.has_script():
            return cls.extract_script()
        else:
            return ""

    @classmethod
    def has_styles(cls) -> bool:
        """Returns True if the component has a css style defined in the class or a file
        in the component directory.

        Follows discovery rules:
        1. Check current class for inline style (takes precedence)
        2. Check current class for external CSS file
        3. Check base classes for inline style
        4. Check base classes for external CSS file
        """
        # Check current class first (inline takes precedence)
        if _has_own_attribute(cls, "style"):
            return True
        # Check current class for external file
        if os.path.exists(cls._get_component_file_path_with_extension("css")):
            return True
        # Check base classes
        for base in cls.__mro__[1:]:
            if hasattr(base, "has_styles") and base is not BasicComponent:
                if base.has_styles():
                    return True
        return False

    @classmethod
    def _is_styles_inline(cls) -> bool:
        """Returns True if the component has inline CSS style.

        Follows discovery rules:
        1. Check current class for inline style (takes precedence)
        2. Check base classes for inline style
        """
        # Check current class first
        if _has_own_attribute(cls, "style"):
            return True
        # Check base classes
        for base in cls.__mro__[1:]:
            if hasattr(base, "_is_styles_inline") and base is not BasicComponent:
                if base._is_styles_inline():
                    return True
        return False

    @classmethod
    def extract_styles(cls) -> str:
        """Returns the CSS styles extracted from either inline or external sources.

        Follows discovery rules:
        1. If current class has inline style, use it
        2. If current class has external CSS file, use it
        3. Check base classes with same rules

        Returns:
            The CSS code as a string
        """
        # Check current class for inline style (takes precedence)
        if _has_own_attribute(cls, "style"):
            source_filename, comp_start_line, source_len = cls.get_source_location()
            with open(source_filename, "r") as f:
                py_source = f.read()
            comp_start_offset = len("\n".join(py_source.split("\n")[:comp_start_line]))
            start = py_source.index(cls.style, comp_start_offset)
            before = py_source[:start]
            before = re.sub(r"\S", " ", before)
            return f"{before}{cls.style}"
        # Check current class for external file
        css_file = cls._get_component_file_path_with_extension("css")
        if os.path.exists(css_file):
            return cls._read_component_file_with_extension("css")
        # Check base classes
        for base in cls.__mro__[1:]:
            if hasattr(base, "extract_styles") and base is not BasicComponent:
                styles = base.extract_styles()
                if styles:
                    return styles
        return ""

    @classmethod
    def render_styles(cls) -> str:
        """Returns the CSS styles defined in the class inline, or from a component's
        CSS file."""

        # for CSS, this is nothing else than returning the styles as string.
        # there is no additional logic here.
        return cls.extract_styles()

    @classmethod
    def as_tag(cls, request, *args, **kwargs) -> SafeString:
        if not hasattr(request, "tetra_components_used"):
            request.tetra_components_used = set()
        request.tetra_components_used.add(cls)
        component = cls(request, *args, **kwargs)
        component.recalculate_attrs(component_method_finished=False)
        return component.render()

    def _call_load(self, *args, **kwargs) -> None:
        self._pre_load(*args, **kwargs)
        self.load(*args, **kwargs)

    def _pre_load(self, *args, **kwargs):
        """Placeholder for code that should be run right before load() is called.
        This can be used for inheriting base classes to auto-load some data,
        but users don't have to call super().load() from their load() implementation
        each time.
        """
        pass

    def load(self, *args, **kwargs) -> None:
        """Override this method to load the component's data, e.g. from the database.

        Caution: Any attributes that are set in this method are NOT saved with the
        state, for efficiency.
        """
        pass

    def _add_self_attrs_to_context(self, context) -> None:
        for key in dir(self):
            if not (
                key.startswith("_") or isclassmethod(getattr(self.__class__, key, None))
            ):
                # if not (key.startswith("_") or isclassmethod(getattr(self, key))):
                context[key] = getattr(self, key)

    def get_context_data(self, **kwargs) -> RequestContext:
        """Update the render context of the component with given kwargs.

        Make sure to call the `super().get_context_data()` method when overriding.
        """
        if isinstance(self._context, RequestContext):
            context = self._context
        else:
            context = RequestContext(self.request, self._context)
        self._add_self_attrs_to_context(context)
        context.update(kwargs)
        return context

    def render(self, **kwargs) -> SafeString:
        return self.renderer.render(**kwargs)

    def recalculate_attrs(self, component_method_finished: bool):
        """Hook for code that should be run before and after user interactions with
        attributes.

        You can add code here that e.g. updates some attributes "in the last moment"
        before rendering, like "dirty" flags that are set when any of the attributes
        have changed, or property attributes that are calculated automatically,
        after component methods have changed other attributes.

        The method is called before and after the component methods are executed.

        Attributes:
            component_method_finished (bool): Whether the recalculation was triggered
                before or after (right before rendering) custom component methods are
                executed. You can react on it differently.
        """


empty = object()


class Public:
    def __init__(self, obj: Any = None, update: bool = True) -> None:
        """
        Decorate a method or attribute with a public decorator.

        This decorator can be used to create methods or attributes that behave like
        public methods or properties. It can be used to add event listeners, watch
        attributes, debounce and throttle functions, and other functionality.

        Example usage:
        class MyComponent(Component):
            my_attribute = public("initial value")

            @public
            def my_method(self):
                ...

            @public
            @watch("my_attribute")
            def my_attribute_changed(self, new_value, old_value, attr):
                print(f"My attribute changed from {old_value} to {new_value}")

        my_component = MyComponent()
        my_component.my_method()  # Output: My method called

        Attributes:
            obj (Any): The object to decorate (method or attribute).
            update (bool): whether update() should be called at the end of the method.
        """
        self._update = update
        self._watch: list[str] = []
        self._debounce = None
        self._debounce_immediate = None
        self._throttle = None
        self._throttle_trailing = None
        self._throttle_leading = None
        self._event_subscriptions: list[str] = []
        self._store_name = None
        self.obj = None
        self.__call__(obj)

    def __call__(self, obj: Any) -> Self:
        if isinstance(obj, Public):
            # Public decorator applied multiple times - combine them
            self._update = obj._update if obj._update else self._update
            self._watch = obj._watch if obj._watch else self._watch
            self._debounce = obj._debounce if obj._debounce else self._debounce
            self._debounce_immediate = (
                obj._debounce_immediate
                if obj._debounce_immediate
                else self._debounce_immediate
            )
            self._throttle = obj._throttle if obj._throttle else self._throttle
            self._throttle_trailing = (
                obj._throttle_trailing
                if obj._throttle_trailing
                else self._throttle_trailing
            )
            self._throttle_leading = (
                obj._throttle_leading
                if obj._throttle_leading
                else self._throttle_leading
            )
            self._event_subscriptions = (
                obj._event_subscriptions
                if obj._event_subscriptions
                else self._event_subscriptions
            )
            self._store_name = obj._store_name if obj._store_name else self._store_name
            self.obj = obj.obj if obj.obj else self.obj

        elif isinstance(obj, FunctionType):
            # `public` decorator applied to a method

            @wraps(obj)
            def fn(instance: "Component", *args, **kwargs):
                if not args and not kwargs and not inspect.signature(obj).parameters:
                    # if the object is a zero-argument callable, call it without instance
                    # this is needed for form field initial values that are callables
                    return obj()

                ret: JsonResponse | FileResponse = obj(instance, *args, **kwargs)
                if self._update:
                    instance.update()
                return ret

            self.obj = fn
        else:
            # `public` is wrapping a variable (str, int, etc)
            self.obj = obj
        return self

    def __getattr__(self, name) -> Any:
        """If an attribute name is requested that does not exist in the class,
        search for `do_<name>` in the class.
        """
        do_name = f"do_{name}"
        if do_name in self.__class__.__dict__:
            return getattr(self, do_name)
        else:
            raise AttributeError(f"Public decorator has no method {name}.")

    def do_watch(self, *args) -> Self:
        if not args:
            raise ValueError(".watch decorator requires at least one argument.")
        for arg in args:
            if isinstance(arg, str):
                self._watch.append(arg)
            else:
                self._watch.extend(arg)
        return self

    def do_debounce(self, timeout, immediate=False) -> Self:
        self._debounce = timeout
        self._debounce_immediate = immediate
        return self

    def do_throttle(self, timeout, trailing=False, leading=True) -> Self:
        self._throttle = timeout
        self._throttle_trailing = trailing
        self._throttle_leading = leading
        return self

    def do_listen(self, event) -> Self:
        """Keeps track of the event for a dynamic event subscription of the component."""
        self._event_subscriptions.append(event)
        return self

    def do_store(self, store_name: str) -> Self:
        """Syncs the property with an Alpine.js store."""
        self._store_name = store_name
        return self


class _PublicFactory:
    """Internal entry point for the ``public`` decorator.

    Using a factory instance (rather than the ``Public`` class directly) avoids
    the need for a metaclass while still allowing the ``public.watch(...)``,
    ``public.debounce(...)``, etc. decorator patterns.
    """

    def __call__(self, obj: Any = None, update: bool = True) -> "Public":
        return Public(obj, update)

    def watch(self, *args) -> "Public":
        return Public().do_watch(*args)

    def debounce(self, timeout, immediate: bool = False) -> "Public":
        return Public().do_debounce(timeout, immediate)

    def throttle(
        self, timeout, trailing: bool = False, leading: bool = True
    ) -> "Public":
        return Public().do_throttle(timeout, trailing, leading)

    def listen(self, event) -> "Public":
        return Public().do_listen(event)

    def store(self, store_name: str) -> "Public":
        return Public().do_store(store_name)


public = _PublicFactory()


tracing_component_load = WeakKeyDictionary()


def is_subclass_of(hint, target_class) -> bool:
    """Check if a type hint is or contains a subclass of target_class."""
    if isinstance(hint, type) and issubclass(hint, target_class):
        return True
    origin = get_origin(hint)
    if origin is UnionType or origin is Union:
        return any(is_subclass_of(arg, target_class) for arg in get_args(hint))
    return False


def _init_component_class(cls) -> None:
    """Process ``@public`` decorated attrs and set component metadata on *cls*.

    This is the ``__init_subclass__``-based replacement for
    ``ComponentMetaClass.__new__``.  It is called from
    ``Component.__init_subclass__`` for every subclass and once explicitly
    for ``Component`` itself right after its class body is evaluated.
    """
    public_methods: list[dict[str, Any]] = list(
        itertools.chain.from_iterable(
            base._public_methods
            for base in cls.__bases__
            if hasattr(base, "_public_methods")
        )
    )
    public_properties: list[str] = list(
        itertools.chain.from_iterable(
            base._public_properties
            for base in cls.__bases__
            if hasattr(base, "_public_properties")
        )
    )
    public_stores: dict[str, str] = {}
    for base in cls.__bases__:
        if hasattr(base, "_public_stores"):
            public_stores.update(base._public_stores)

    for attr_name in list(cls.__dict__.keys()):
        attr_value = cls.__dict__[attr_name]

        if isinstance(attr_value, Public):
            # Replace the Public wrapper with the underlying object so that
            # ordinary attribute / method access works as expected.
            setattr(cls, attr_name, attr_value.obj)

            if isinstance(attr_value.obj, FunctionType):
                # the decorated object is a method
                fn = attr_value.obj
                pub_met = {"name": attr_name}
                if attr_value._watch:
                    if not param_names_exist(fn, "value", "old_value", "attr"):
                        raise ValueError(
                            f"The .watch method `{attr_name}` must have 'value', "
                            f"'old_value' and 'attr' as arguments."
                        )
                    pub_met["watch"] = attr_value._watch
                if attr_value._debounce:
                    pub_met["debounce"] = attr_value._debounce
                    pub_met["debounce_immediate"] = attr_value._debounce_immediate
                if attr_value._throttle:
                    pub_met["throttle"] = attr_value._throttle
                    pub_met["throttle_trailing"] = attr_value._throttle_trailing
                    pub_met["throttle_leading"] = attr_value._throttle_leading
                if attr_value._event_subscriptions:
                    pcount = param_count(fn)
                    if pcount != 1:
                        raise ValueError(
                            f"Event listener method '{attr_name}' has wrong "
                            f"number of arguments. Expected 2 (self, "
                            f"event_detail), but got {pcount}."
                        )
                    pub_met["event_subscriptions"] = attr_value._event_subscriptions
                public_methods.append(pub_met)
            else:
                public_properties.append(attr_name)
                if attr_value._store_name:
                    store_path = attr_value._store_name
                    # If store path doesn't include property path, append attribute name
                    if "." not in store_path:
                        store_path = f"{store_path}.{attr_name}"
                    public_stores[attr_name] = store_path

    cls._public_methods = public_methods
    cls._public_properties = public_properties
    cls._public_stores = public_stores

    # Handle Pydantic model creation here, AFTER cls is created and fully populated.
    # This ensures that dynamic attributes from e.g., FormComponent.__init_subclass__
    # are available in cls._public_properties and cls.__annotations__.
    if not cls.__dict__.get("__abstract__", False):
        from pydantic import create_model, ConfigDict

        public_fields = {}
        for prop in cls._public_properties:
            # Get type hint if available
            hint = Any
            # Check cls.__annotations__ which includes all hints for this class
            if hasattr(cls, "__annotations__") and prop in cls.__annotations__:
                hint = cls.__annotations__[prop]
            else:
                # Fallback to MRO
                for base in cls.__mro__:
                    if (
                        hasattr(base, "__annotations__")
                        and prop in base.__annotations__
                    ):
                        hint = base.__annotations__[prop]
                        break

            # Normalize the hint
            if hint is not Any:
                try:
                    inner_hint = hint
                    if get_origin(hint) is Union:
                        args = get_args(hint)
                        if NoneType in args:
                            inner_hint = next(
                                (a for a in args if a is not NoneType), Any
                            )

                    if inner_hint is NoneType:
                        # If it's just NoneType, it means we don't know the type,
                        # so treat as Any.
                        hint = Any
                    elif isinstance(inner_hint, type) and issubclass(
                        inner_hint, UploadedFile
                    ):
                        # In ModelForm, FileFields might contain FieldFile (e.g. from instance)
                        # which are not UploadedFile. So we allow Any here if it's not a new upload.
                        hint = Any
                    elif inner_hint is Any or (
                        isinstance(inner_hint, type)
                        and inner_hint.__module__ != "builtins"
                        and not issubclass(inner_hint, (Enum, models.Model))
                    ):
                        hint = Any
                except TypeError:
                    pass

            # Use default value from cls.
            # If the property is in the current class's dict, it's the default.
            # If it's inherited, we use Ellipsis (...) to indicate it's required
            # if it has no default in the hierarchy.
            if prop in cls.__dict__:
                default_value = cls.__dict__[prop]
                if isinstance(default_value, Public):
                    default_value = default_value.obj
            else:
                # Check if any base has a default value
                default_value = ...
                for base in cls.__mro__:
                    if prop in base.__dict__:
                        default_value = base.__dict__[prop]
                        if isinstance(default_value, Public):
                            default_value = default_value.obj
                        break

            public_fields[prop] = (hint, default_value)

        cls._StateModel = create_model(
            f"{cls.__name__}State",
            **public_fields,
            __config__=ConfigDict(arbitrary_types_allowed=True),
        )


class Component(BasicComponent):
    __abstract__ = True
    script: Optional[str] = None
    _callback_queue = None
    _excluded_props_from_saved_state = [
        "request",
        "_callback_queue",
        "_loaded_children_state",
        "_excluded_load_props_from_saved_state",
        "_is_resumed_from_state",
        "_resumed_from_state_data",
        "_event_subscriptions",
        "__abstract__",
        "_temp_files",
        "_is_directory_component",
        "_context",
    ]
    _excluded_load_props_from_saved_state: list[str] = []
    _loaded_children_state = None
    _load_args: tuple = ()
    _load_kwargs: dict[str, Any] = {}
    _resumed_from_state_data: ComponentData
    # _temp_files is an internal dict to track which data attributes are files.
    _temp_files: dict[str, UploadedFile] = {}
    key = public(None)

    def __init_subclass__(cls, **kwargs):
        # Capture whether _name/_library were set *explicitly* in this class body
        # before super() may modify them (BasicComponent sets _name in its hook).
        body_had_name = "_name" in cls.__dict__
        body_had_library = "_library" in cls.__dict__
        # Compile template and set underscore _name via BasicComponent
        super().__init_subclass__(**kwargs)
        # Process @public decorated attrs and (if concrete) create StateModel
        _init_component_class(cls)
        # Reset _library and _name so each class starts fresh; the library
        # registration system will set _name to the registered name later.
        if not body_had_name:
            cls._name = None
        if not body_had_library:
            cls._library = None

    def __init__(
        self,
        _request: TetraHttpRequest | HttpRequest,
        _attrs: dict[str, Any] | None = None,
        _context: dict[str, Any] | RequestContext | None = None,
        _slots=None,
        key: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        self._load_args = ()
        self._load_kwargs = {}
        self._excluded_load_props_from_saved_state = []
        self._temp_files = {}
        super().__init__(
            _request,
            _attrs,
            _context,
            _slots,
            key,
            *args,
            **kwargs,
        )
        self.key = self.attrs.get("key")
        self.renderer = ComponentRenderer(self)

    def _get_state_adapter(self):
        # Created once per class, not per instance
        from pydantic import TypeAdapter

        return TypeAdapter(self._StateModel)

    @classmethod
    def from_state(
        cls,
        component_state: ComponentData,
        request: HttpRequest,
        key: str | None = None,
        _attrs=None,
        _context=None,
        _slots=None,
        *args,
        **kwargs,
    ) -> Any:
        """Creates and initializes a component instance from its serialized state.

        This method reconstructs a component from its encrypted state data, typically
        received from the client after a previous server interaction. It handles:

        - Decrypting and validating the component state
        - Restoring component attributes and properties
        - Resolving Django Model instances from their primary keys
        - Managing uploaded files and their temporary storage
        - Re-executing the component's load() method with original arguments
        - Updating public properties from client-side changes

        Args:
            component_state: Dictionary containing 'encrypted' state string and 'data'
                dict with current client-side property values
            request: The current HTTP request object
            key: Optional component key for identification
            _attrs: Optional attributes to set on the component
            _context: Optional template context to use
            _slots: Optional template slots to use
            *args: Positional arguments to pass to load()
            **kwargs: Keyword arguments to pass to load()

        Returns:
            Component: A fully initialized component instance with restored state

        Raises:
            TypeError: If component_state structure is invalid
            AttributeError: If required state attributes are missing

        Note:
            - Model fields are automatically fetched from the database using their PKs
            - File fields maintain references to temporary uploaded files
            - The component's load() method is called with the original arguments
            - Client-side property changes override the encrypted state values
        """
        if not isinstance(component_state, dict):
            raise TypeError("Encrypted state has wrong type")
        if "encrypted" not in component_state:
            raise AttributeError("No 'encrypted' attribute in component_state")
        if not isinstance(component_state["encrypted"], str):
            raise TypeError(
                f"Encrypted state has wrong type: {type(component_state['encrypted'])}"
            )
        if "data" not in component_state:
            raise AttributeError("No 'data' attribute in encrypted state")
        if not isinstance(component_state["data"], dict):
            raise TypeError("Invalid component state 'data' type.")

        component = decode_component(component_state["encrypted"], request)
        if not isinstance(component, cls):
            raise TypeError(
                f"Component '{component.__class__.__name__}' of invalid "
                f"type, should be: {cls.__name__}."
            )

        component.request = request
        # Set default values for attributes if they don't exist
        for attr, default in [
            ("_context", {}),
            ("attrs", {}),
            ("_temp_files", {}),
            ("_slots", None),
        ]:
            if not hasattr(component, attr):
                setattr(component, attr, default)

        # Override with provided values if given
        if key:
            component.key = key
        if _attrs:
            component.attrs = _attrs
        if _context:
            component._context = _context
        if _slots:
            component._slots = _slots
        if args:
            component._load_args = args
        if kwargs:
            component._load_kwargs = kwargs

        if isinstance(component, Component):
            component.renderer = ComponentRenderer(component)
        else:
            component.renderer = BaseRenderer(component)

        # Try to reload the component state. If the component's load() method
        # fails because database objects no longer exist, raise a StaleComponentStateError
        try:
            component._recall_load()
        except (ObjectDoesNotExist, AttributeError) as e:
            # Check if this is truly a stale state error (e.g., accessing attribute on None)
            # or a legitimate programming error in the load() method
            error_msg = str(e)
            if (
                "DoesNotExist" in e.__class__.__name__
                or "has no attribute" in error_msg
                or "NoneType" in error_msg
            ):
                raise StaleComponentStateError(
                    f"Component '{cls.__name__}' state is stale: {error_msg}. "
                    f"The data it references may have been deleted or modified by another client."
                ) from e
            # Re-raise if it's not a stale state issue
            raise

        # get data from client and populate component attributes with it
        for key, state_value in component_state["data"].items():
            # try to get attribute type (from the class annotations created when the
            # component was declared)
            AttributeType = component.__annotations__.get(key, NoneType)

            # if client data type is a model, try to see the value in the
            # recovered data as Model.pk and get the model again.
            if is_subclass_of(AttributeType, Model):
                if state_value:
                    # FIXME: this hits the database, before the actual (and probably
                    #  different) value is set via e.g. the load() method.
                    #  Find a way to only load the model when needed.
                    if isinstance(AttributeType, type) and issubclass(
                        AttributeType, Model
                    ):
                        state_value = AttributeType.objects.get(pk=state_value)
                    else:
                        # If it's a Union/Optional, we need to find the Model class
                        for arg in get_args(AttributeType):
                            if isinstance(arg, type) and issubclass(arg, Model):
                                state_value = arg.objects.get(pk=state_value)
                                break
                else:
                    state_value = None  # or attr_type.objects.none()

            # if the data type is a file, try to find the file by its path
            elif is_subclass_of(AttributeType, UploadedFile):
                if state_value:
                    # if the file was reconstructed from the client data (which
                    # doesn't contain the temp_path anymore), recover the temp_path
                    # from the original state (decoded from the encrypted token)
                    if getattr(state_value, "_reconstructed", False):
                        original_value = getattr(component, key, None)
                        if isinstance(original_value, NamedTemporaryUploadedFile):
                            # reuse the original file handle.
                            state_value.file = original_value.file
                        else:
                            # if the file is not in the original state, it means it
                            # was not uploaded by this user in a previous request.
                            state_value = None

                    if not state_value:
                        continue

                    # the value (temp file path) from the saved component client state
                    # could be stale, as the file could be already saved as permanent
                    # file in MEDIA_ROOT/* somewhere using submit() in another session.
                    # Then the state's file_path is wrong. in this case,
                    # delete this state!
                    if not state_value.file or not os.path.exists(
                        state_value.file.name
                    ):
                        component_state["data"][key] = None
                        if key in component._temp_files:
                            del component._temp_files[key]

                else:
                    # if there is no valid file in the request, it means the file was
                    # not correctly uploaded or removed from the input field,
                    # so just skip it
                    continue

                # save file in a separate dict so we can access it easier
                component._temp_files[key] = state_value

            setattr(component, key, state_value)

        component._is_resumed_from_state = True
        component._resumed_from_state_data = component_state["data"]
        component.recalculate_attrs(component_method_finished=False)
        return component

    @classmethod
    def _component_url(cls) -> str:
        """Returns the single Tetra call endpoint URL"""
        return reverse("tetra:component-call")

    @classmethod
    def has_script(cls) -> bool:
        """Returns True if the component has a javascript script part, else False.

        Follows discovery rules:
        1. Check current class for inline script (takes precedence)
        2. Check current class for external JS file
        3. Check base classes for inline script
        4. Check base classes for external JS file
        """
        # Check current class first (inline takes precedence)
        if _has_own_attribute(cls, "script"):
            return True
        # Check current class for external file
        if os.path.exists(cls._get_component_file_path_with_extension("js")):
            return True
        # Check base classes
        for base in cls.__mro__[1:]:
            if hasattr(base, "has_script") and base not in (Component, BasicComponent):
                if base.has_script():
                    return True
        return False

    @classmethod
    def _is_script_inline(cls) -> bool:
        """Returns True if the component has inline JavaScript script.

        Follows discovery rules:
        1. Check current class for inline script (takes precedence)
        2. Check base classes for inline script
        """
        # Check current class first
        if _has_own_attribute(cls, "script"):
            return True
        # Check base classes
        for base in cls.__mro__[1:]:
            if hasattr(base, "_is_script_inline") and base not in (
                Component,
                BasicComponent,
            ):
                if base._is_script_inline():
                    return True
        return False

    @classmethod
    def extract_script(cls) -> str:
        """This method extracts the component's JavaScript, from wherever it finds
        it, and returns it.

        Follows discovery rules:
        1. If current class has inline script, use it
        2. If current class has external JS file, use it
        3. Check base classes with same rules

        Returns:
            The JavaScript code as a string, extracted from either the inline
                script property or an external .js file.
        """
        # Check current class for inline script (takes precedence)
        if _has_own_attribute(cls, "script"):
            source_filename, comp_start_line, source_len = cls.get_source_location()
            with open(source_filename, "r") as f:
                py_source = f.read()
            comp_start_offset = len("\n".join(py_source.split("\n")[:comp_start_line]))
            start = py_source.index(cls.script, comp_start_offset)
            before = py_source[:start]
            before = re.sub(r"\S", " ", before)
            return f"{before}{cls.script}"
        # Check current class for external file
        js_file = cls._get_component_file_path_with_extension("js")
        if os.path.exists(js_file):
            return cls._read_component_file_with_extension("js")
        # Check base classes
        for base in cls.__mro__[1:]:
            if hasattr(base, "extract_script") and base not in (
                Component,
                BasicComponent,
            ):
                script = base.extract_script()
                if script:
                    return script
        return ""

    @classmethod
    def render_script(cls, component_var=None) -> str:
        """This method dynamically generates the complete JavaScript module for the
        component.

        It consists of the component's methods, attributes, and server-side methods,
        including custom JavaScript code from the script property or a .js file in
        the component's directory.

        This script can be imported dynamically via Alpine.init() and used to update
        the component's state.
        """
        component_server_methods = []
        # Get the single endpoint URL for all component calls
        endpoint_url = cls._component_url()

        for method in cls._public_methods:
            method_data = copy(method)
            method_data["endpoint"] = endpoint_url
            component_server_methods.append(method_data)

        # Always add _refresh as an internal method for reactive components
        # This ensures the endpoint is always available without hardcoding
        component_server_methods.append({"name": "_refresh", "endpoint": endpoint_url})

        if not component_var:
            component_var = cls.extract_script() if cls.has_script() else "{}"

        # Component location metadata for the unified endpoint
        component_metadata = {
            "app_name": cls._library.app.label,
            "library_name": cls._library.name,
            "component_name": cls._name,
        }

        return render_to_string(
            "script.js",
            {
                "component_name": cls.full_component_name(),
                "component_script": component_var,
                "component_server_methods": to_json(component_server_methods),
                "component_server_properties": to_json(cls._public_properties),
                "component_metadata": to_json(component_metadata),
            },
        )

    def _call_load(self, *args, **kwargs) -> None:
        """Load the component's state and attributes.
        It keeps a record of the given parameters for later recalls and
        then calls the (user defined) load method of the component.
        """
        self._load_args = args
        self._load_kwargs = kwargs
        # prevent properties set in load() to be saved with the state
        tracing_component_load[self] = set()
        try:
            self._pre_load(*args, **kwargs)
            self.load(*args, **kwargs)
            props = tracing_component_load[self]
        finally:
            del tracing_component_load[self]
        self._excluded_load_props_from_saved_state = list(props)

    def _recall_load(self) -> None:
        """Re-execute the load method of the component with the same arguments that
        were used when the component was initially loaded."""
        self._call_load(*self._load_args, **self._load_kwargs)

    def __setattr__(self, item, value) -> None:
        """Special method that allows attributes to be set on the component. It also
        tracks which attributes are being set so that they can be included in the
        component's state.
        """
        if self in tracing_component_load:
            # TODO: maybe File is too broad? FieldFile, UploadedFile?
            if not isinstance(value, File):
                tracing_component_load[self].add(item)
        return super().__setattr__(item, value)

    @property
    def client(self) -> CallbackList:
        if self._callback_queue is None:
            self._callback_queue = CallbackList()
        return self._callback_queue

    def set_load_args(self, *args, **kwargs) -> None:
        load_args = {
            "args": args,
            "kwargs": kwargs,
        }
        try:
            to_json(load_args)
        except TypeError:
            raise ComponentError(
                f"Tetra Component {self.__class__.__name__} tried to self.set_load_args() with a none json serializable value."
            )
        self._load_args = args
        self._load_kwargs = kwargs

    def _data(self) -> dict[str, Any]:
        """
        Returns a dictionary of public properties suitable for state validation.
        Converts non-serializable objects (like PhoneNumber) to their string representation
        for proper serialization and validation.
        """
        data = {}
        for key in self._public_properties:
            value = getattr(self, key)

            # Normalize empty strings to None for enum types
            # This handles Django's convention where optional ChoiceFields submit ""
            if value == "" and key in self.__annotations__:
                annotation = self.__annotations__[key]
                # Check if the field is an Optional[Enum]
                origin = get_origin(annotation)
                if origin is Union:
                    args = get_args(annotation)
                    for arg in args:
                        if (
                            arg is not NoneType
                            and isinstance(arg, type)
                            and issubclass(arg, Enum)
                        ):
                            value = None
                            break

            # Convert non-serializable types to strings
            if value is not None and not isinstance(value, SERIALIZABLE_TYPES):
                value = str(value)
            data[key] = value
        return data

    def get_extra_tags(self) -> dict[str, str | None]:
        extra_tags = super().get_extra_tags()
        extra_tags.update(
            {
                "tetra-component": f"{self.full_component_name()}",
                "x-bind": "__rootBind",
            }
        )
        return extra_tags

    def _convert_model_pks_to_instances(self) -> None:
        """
        Convert pk values (strings/ints) to Model instances for public properties.

        This is called before serialization and validation to ensure that Model fields
        annotated as Django Models receive actual instances instead of pk values.
        The conversion happens in-place, updating the component's attributes.

        Design Note:
        This conversion is done at the component level (not in the pickler) because:
        1. Only the component has access to type annotations needed for conversion
        2. The conversion happens once and updates the component in-place
        3. The Model pickler can then handle instances normally without type metadata
        4. Database queries only occur when actually needed (serialization/validation)
        """
        # Get annotations from the class hierarchy
        annotations = {}
        for cls in type(self).__mro__:
            if hasattr(cls, "__annotations__"):
                annotations.update(cls.__annotations__)

        if not annotations:
            return  # No annotations, nothing to convert

        for key in getattr(self, "_public_properties", []):
            value = getattr(self, key, None)
            if value is None or isinstance(value, models.Model):
                continue  # Already a Model instance or None

            annotation = annotations.get(key, NoneType)
            if annotation is NoneType:
                continue

            # Check if the annotation indicates a Model type
            if is_subclass_of(annotation, models.Model):
                # Try to convert pk to Model instance
                model_class: Optional[type[Model]] = None
                if isinstance(annotation, type) and issubclass(
                    annotation, models.Model
                ):
                    model_class = annotation
                else:
                    # If it's a Union/Optional, find the Model class
                    for arg in get_args(annotation):
                        if isinstance(arg, type) and issubclass(arg, models.Model):
                            model_class = arg
                            break

                if model_class:
                    try:
                        instance = model_class.objects.get(pk=value)
                        setattr(self, key, instance)
                    except (model_class.DoesNotExist, ValueError, TypeError):
                        # If we can't fetch it, leave as-is
                        # This will cause validation to fail with appropriate error
                        pass

    def _encoded_state(self) -> str:
        # Validates and serializes the current __dict__ values
        # Convert pk values to Model instances before validation
        self._convert_model_pks_to_instances()
        data = self._data()
        self._get_state_adapter().validate_python(data)
        return encode_component(self)

    def __getstate__(self) -> dict[str, Any]:
        # Convert pk values to Model instances before pickling
        # This ensures the Model pickler receives proper instances
        self._convert_model_pks_to_instances()

        state = self.__dict__.copy()
        if "renderer" in state:
            del state["renderer"]

        # Access class attribute directly to avoid instance attribute shadowing
        # Collect exclusions from the entire class hierarchy
        excluded_props = []
        for cls in self.__class__.__mro__:
            if hasattr(cls, "_excluded_props_from_saved_state"):
                # Get the class attribute, not instance attribute
                excluded_props.extend(
                    getattr(cls, "_excluded_props_from_saved_state", [])
                )

        # Also include instance-specific exclusions
        excluded_props.extend(
            getattr(self, "_excluded_load_props_from_saved_state", [])
        )

        # Remove duplicates while preserving order
        seen = set()
        for prop_name in excluded_props:
            if prop_name not in seen:
                seen.add(prop_name)
                if prop_name in state:
                    del state[prop_name]

        return state

    def _render_data(self) -> dict[str, Any]:
        """Returns a dictionary that includes the component's attributes and a
        special attribute __state that contains the component's encoded state as a JSON
        string.
        This dictionary is used to render the component's HTML.
        """
        data = self._data()
        data["__state"] = self._encoded_state()
        if hasattr(self, "_public_stores") and self._public_stores:
            data["__serverStores"] = self._public_stores
        return data

    def _add_self_attrs_to_context(self, context) -> None:
        super()._add_self_attrs_to_context(context)
        if hasattr(self, "_loaded_children_state") and self._loaded_children_state:
            children_state = {}
            for c in self._loaded_children_state:
                child_key = c.get("data", {}).get("key")
                if child_key:
                    children_state[child_key] = c
            context["_loaded_children_state"] = children_state
        else:
            context["_loaded_children_state"] = None

    def render(self, mode=RenderDataMode.INIT, **kwargs) -> SafeString:
        """Renders the component's HTML.

        It makes the following decisions based on the given mode:
        - If mode is RenderDataMode.INIT (the default), just renders the component's
            data into `x-data`. The client will use it as Alpine data.
        - If mode is RenderDataMode.MAINTAIN, it instructs the client to just copy the
            original `x-data` to the updated component element, so no data changes.
        - If mode is RenderDataMode.UPDATE, the client will be instructed to replace
            the existing `x-data` with new data from the server state
        """
        return self.renderer.render(mode=mode, **kwargs)

    def update_html(self, include_state=False) -> None:
        """Updates the component's HTML.

        If `include_state` is True, it includes the component's state in the HTML.
        Otherwise, it only includes the component's attributes and instructs the
        client to not change the client side data.
        """
        if include_state:
            self.client._updateHtml(self.render(mode=RenderDataMode.UPDATE))
        else:
            self.client._updateHtml(self.render(mode=RenderDataMode.MAINTAIN))

    def update_data(self) -> None:
        """Updates the component's state with the latest data from the server."""
        self.client._updateData(self._render_data())

    def update(self) -> None:
        """Updates the component's HTML and state."""
        self.update_html(include_state=True)

    def replace_component(self) -> None:
        """Replaces the current component with a new one. It first creates a new
        component with the same name and attributes as the current component and
        inserts it into the DOM, and then removes the current component from the DOM.
        """
        self.client._replaceComponent(self.render())

    def push_url(self, path: str) -> None:
        """Pushes a new URL path to the browser's history."""
        self.client._pushUrl(path)
        self.request.tetra.set_url_path(path)

    def update_search_param(self, param: str, value: str | int = None):
        """Updates a URL query parameter. Leaves alone tho other params, if any.

        Args:
            param: The name of the URL search parameter to be updated.
            value: The new value for the parameter. Defaults to None, which means that
                the parameter is deleted from the URL.
        """
        self.client._updateSearchParam(param, value)
        self.request.tetra.set_url_query_param(param, value)

    def replace_url(self, url: str) -> None:
        """Replaces the current URL with a new one."""
        self.client._pushUrl(url, replace=True)
        self.request.tetra.set_url(url)

    def _call_public_method(
        self, request, method_name, children_state, *args
    ) -> JsonResponse | FileResponse:
        try:
            self._loaded_children_state = children_state
            self._callback_queue = CallbackList()
            result = getattr(self, method_name)(*args)
            callbacks = self._callback_queue.serialize()
            self._callback_queue = None
            libs = list(
                set(component._library for component in request.tetra_components_used)
            )

            # if the response is a FileResponse, we directly return the result.
            if isinstance(result, FileResponse):
                result.as_attachment = True
                return result
            else:
                # Collect Django messages
                messages = []
                for message in get_messages(request):
                    if not hasattr(message, "uid"):
                        import uuid

                        message.uid = str(uuid.uuid4())
                    messages.append(message)

                return JsonResponse(
                    {
                        "protocol": "tetra-1.0",
                        "type": "call.response",
                        "success": True,
                        "payload": {
                            "result": result,
                        },
                        "metadata": {
                            "styles": [lib.styles_url for lib in libs],
                            "js": [lib.js_url for lib in libs],
                            "messages": messages,
                            "callbacks": callbacks,
                        },
                    },
                    encoder=TetraJSONEncoder,
                )
        except Exception as e:
            logger.exception("Error calling public method %s", method_name)
            return JsonResponse(
                {
                    "protocol": "tetra-1.0",
                    "type": "call.response",
                    "success": False,
                    "error": {
                        "code": e.__class__.__name__,
                        "message": str(e),
                    },
                },
                status=500,
            )

    @public
    def _refresh(self) -> None:
        """Re-render and return
        This is just a noop as the @public decorator implements this functionality
        """


# Bootstrap Component itself: __init_subclass__ only fires for subclasses, so we
# must manually run the same initialisation for the Component base class.
_init_component_class(Component)
Component._name = None
Component._library = None


def get_python_type_from_form_field(field, initial) -> type:
    """
    Derives the Python type from a Django form field.

    Args:
        field: A Django form field instance

    Returns:
        The corresponding Python type. If it can't be determined, return NoneType
    """
    # The order of this map is important, as some fields derive from others. If we
    # checked a field against IntegerField before checking agains FloatField,
    # it would be True, even if it was a FloatField. We could have checked with "is"
    # or "==", but then we would have lost the ability to handle future or
    # existing field types derived from these base types.
    field_type_map = {
        forms.FloatField: float,
        forms.DecimalField: Decimal,
        forms.IntegerField: int,
        forms.BooleanField: bool,
        forms.DateField: date,
        forms.DateTimeField: datetime,
        forms.TimeField: time,
        forms.EmailField: str,
        forms.URLField: str,
        forms.CharField: str,
        forms.ChoiceField: str,
        forms.ImageField: UploadedFile | FieldFile | File,
        forms.FileField: UploadedFile | FieldFile | File,
    }

    # Check for ModelChoiceField first (special case)
    if isinstance(field, ModelChoiceField):
        return field.queryset.model

    # Fallback: try to infer from initial value
    if initial is not None:
        if isinstance(initial, Enum):
            return type(initial)

    # Check against field type map
    for field_class, python_type in field_type_map.items():
        if isinstance(field, field_class):
            return python_type

    # Fallback: try to infer from initial value
    if initial is not None:
        initial = field.to_python(initial)
        python_type = type(initial)
        if python_type.__module__ == "builtins":
            return python_type
        return Any
    return Any


class FormComponent(Component):
    """
    Component that can render a form, validate and submit it.

    The form itself is not saved with the client state, as pickling forms is somehow
    complicated. Instead, it is recreated with every request and filled with the
    current component attribute values.

    Attributes:
        form_class (type(BaseForm)):
            The form class to use for this component. All fields of the form are
            dynamically created as public attributes in the component,
            and initialized with the form's fields' initial values.
    """

    __abstract__ = True
    form_class: Optional[type[forms.ModelForm]] = None
    form_submitted: bool = False
    form_errors: dict = {}  # TODO: make protected + include in render context
    _form: Form = None
    _validate_called: bool = False

    _excluded_props_from_saved_state = Component._excluded_props_from_saved_state + [
        "_form",
        "_validate_called",
        "form_errors",
    ]

    def __init_subclass__(cls, **kwargs):
        """Add a public component attribute for every field in ``form_class``."""
        form_class = cls.__dict__.get("form_class", None)
        # Ensure the class has its own __annotations__ dict (not inherited).
        if "__annotations__" not in cls.__dict__:
            cls.__annotations__ = {}
        if form_class:
            for field_name, field in form_class.base_fields.items():
                initial = field.initial
                # Try to read the type of the component attribute from the form field.
                python_type = get_python_type_from_form_field(field, initial)
                # Form fields should always be Optional because they can be None
                # or empty initially, and Django's form validation handles the
                # "required" check, not the component state.
                python_type = Optional[python_type]
                setattr(cls, field_name, public(initial))
                cls.__annotations__[field_name] = python_type
        super().__init_subclass__(**kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.form_class:
            raise AttributeError(
                f"Error in {self.__class__.__name__}: The 'form_class' attribute is not set."
            )

    def recalculate_attrs(self, component_method_finished: bool):
        if component_method_finished:
            # Don't show form errors if form is not submitted yet
            if not self.form_submitted:
                self._form.errors.clear()
            # If form was submitted, ensure it's validated so errors are available
            else:
                # Trigger validation if not already done
                _ = self._form.errors
        else:
            self._form = self.get_form()

    def get_context_data(self, **kwargs) -> RequestContext:
        if "form" not in kwargs:
            kwargs["form"] = self._form
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        # Exclude file fields from data dict to prevent file information leaking
        # into rendered HTML. File fields should only be in the files dict.
        # We check the form's base_fields to identify which fields are FileFields.
        file_field_names = {
            name
            for name, field in self.form_class.base_fields.items()
            if isinstance(field, FileField)
        }
        # TODO: better include this directly into ._data()?
        data = {
            key: value
            for key, value in self._data().items()
            if key not in file_field_names
        }
        kwargs = {
            # "initial": self.get_form_initial(), # TODO?
            # "prefix": self.get_prefix(), # TODO?
            "data": data,
            "files": self._temp_files,
        }
        return kwargs

    # def get_form_initial(self):
    #     return {}

    def get_form(self):
        """Returns a new form instance, initialized with data from the component
        attributes."""
        cls = self.form_class
        form = cls(**self.get_form_kwargs())
        self._add_alpine_models_to_fields(form)
        return form

    def _add_alpine_models_to_fields(self, form, prefix: str = None) -> None:
        """Connects the form's fields to the Tetra backend using x-model attributes."""
        for field_name, field in form.fields.items():
            if isinstance(field, FileField):
                # TODO: this is not necessary any more
                form.fields[field_name].widget.attrs.update(
                    {"@change": f"{field_name}=$event.target.files?.[0];"}
                )

                # form.fields[field_name].initial = getattr(self, field_name)
            else:
                if prefix is None:
                    prefix = ""
                if prefix and prefix[:-1] != ".":
                    prefix += "."
                # form.fields[field_name].initial = getattr(self, field_name)
                form.fields[field_name].widget.attrs.update(
                    {"x-model": prefix + field_name}
                )

    @public
    def validate(self, field_names: str | list | None = None) -> dict:
        """Validates the data using the form defined in `form_class`, and re-renders
        the component, without saving the form."""

        if self._validate_called:
            return self.form_errors
        self._validate_called = True

        if self._form:
            form_errors = self._form.errors.get_json_data(escape_html=True)

            # Synchronize existing errors with current form errors
            if self.form_errors:
                self.form_errors = {
                    key: value
                    for key, value in self.form_errors.items()
                    if key in form_errors
                }

            if type(field_names) is str:
                field_names = [field_names]
            # Update errors based on provided field names or include all form errors
            if field_names is not None:
                self.form_errors.update(
                    {
                        key: value
                        for key, value in form_errors.items()
                        if key in field_names
                    }
                )
            else:
                self.form_errors.update(form_errors)
        return self.form_errors

    def form_valid(self, form: BaseForm) -> None:
        """This method is called when the form data is valid.
        It should save the form data.

        Parameters:
            form: The form instance that contains the validated form data.
        """

    def form_invalid(self, form: BaseForm) -> None:
        """Hook that gets called when form was validated with errors. Override this
        method to customize behaviour.

        Parameters:
            form: The form instance that contains the invalid form data.
        """

    def _call_public_method(
        self, request, method_name, children_state, *args
    ) -> JsonResponse | FileResponse:
        """Override to automatically submit form when files are uploaded.

        When files are uploaded via any component method call, they need to be
        processed immediately since browser file inputs are cleared on subsequent
        requests. This method checks if files were uploaded and automatically
        validates the form before calling the requested method.
        """
        # Check if any files were uploaded in this request
        has_uploaded_files = bool(self._temp_files)

        # If files were uploaded and the method is not already submit(),
        # automatically validate and process the form first
        if has_uploaded_files and method_name != "submit":
            self._process_form()

        # Now call the original method
        return super()._call_public_method(request, method_name, children_state, *args)

    def _process_form(self) -> None:
        """Internal method to validate and process the form.

        This is called both by submit() and automatically when files are uploaded.
        """
        self.form_submitted = True

        if self._form.is_valid():
            self.form_valid(self._form)
        else:
            self.form_errors = self._form.errors.get_json_data(escape_html=True)
            # set the possibly cleaned values back to the component's attributes
            for attr, value in self._form.cleaned_data.items():
                setattr(self, attr, value)
            self.form_invalid(self._form)

    @public
    def submit(self) -> None:
        """Submits the form.

        The component will validate the data against the form, and if the form is valid,
        it will call form_valid(), else form_invalid().
        """
        self._process_form()

    def _reset(self):
        """Internally resets all form fields to their defaults set in load(). This
        internal method is not exposed as a
        public API and can be called by load() too. For client side calls use reset() instead.
        """

        # first, clear all temporary files saved in the component
        try:
            for attr_name, file in self._temp_files.items():
                self._temp_files.pop(attr_name)
                self.client._setValueByName(attr_name, "")
                os.remove(file.name)
        except FileNotFoundError:
            # ignore any errors during file removal, file might be already deleted.
            pass

        # second, get a new form without any data, with just initial values of the
        # Form class

        self.form_submitted = False
        self._form = self.get_form()

        self._set_attrs_from_form_class_initial()

        # third, call load() again to apply the initial values meant by the component
        self._recall_load()

    def _set_attrs_from_form_class_initial(self):
        """Get 'initial' values from the form class and set them to the component's
        attributes."""
        # for field_name, field in self.form_class.base_fields.items():
        #     setattr(self, field_name, field.initial)
        #     if self.client and isinstance(field, FileField):
        #         # we additionally have to set the initial value of FileFields to an empty string
        #         # as the browser doesn't set the input field
        #         self.client._setValueByName(field_name, "")

    @public
    def reset(self):
        """Convenience method to be called by the frontend to reset the form.

        All values will be reset to the initial object values.
        """
        self._reset()


class ModelFormComponent(FormComponent):
    """
    Component that can render a Model object using a ModelForm, load and
    save the given object, and validate it. This is basically the equivalent of the
    UpdateView/CreateView class for views in Django.

    Like FormComponent, the class mirrors all FormFields to the component's
    attributes which are then automatically available in the template and the client
    as Javascript/Alpine.js data. When a component attribute is set,
    it is automatically copied into the form instance's properties.

    Attributes:
        form_class (type(ModelForm)): the ModelForm class to use
        model (type(models.Model)): the Model class to use, as alternative to form_class
        fields (list[str]|str): the fields to use in the form, as list, or "__all__" to use all fields
        _context_object_name (str): the name of the context object in the template (TODO)
    """

    __abstract__ = True
    form_class: Optional[type[forms.ModelForm]] = None
    model: ModelBase = None
    object: models.Model = None
    fields: Optional[list[str]] = None
    _context_object_name = None  # TODO
    _excluded_props_from_saved_state = (
        FormComponent._excluded_props_from_saved_state
        + ["_context_object_name", "model", "fields"]
    )

    def __init_subclass__(cls, **kwargs):
        """Validate or auto-create ``form_class`` from ``model``/``fields``."""
        # Ensure the class has its own __annotations__ dict (not inherited).
        if "__annotations__" not in cls.__dict__:
            cls.__annotations__ = {}
        if "__abstract__" not in cls.__dict__:
            model = cls.__dict__.get("model", None)
            abstract = cls.__dict__.get("__abstract__", False)
            # if no form_class nor model/fields is defined in the new class -> Error
            if (
                not cls.__dict__.get("form_class", None)
                and (not model or not cls.__dict__.get("fields", None))
                and not abstract
            ):
                raise AttributeError(
                    f"{cls.__name__} class requires either a 'form_class' or 'model' and "
                    "'fields' attributes"
                )

            # if form_class is not provided, but model/fields, create a form_class on
            # the fly.
            if "form_class" in cls.__dict__:
                form_class = cls.__dict__["form_class"]
                if not issubclass(form_class, forms.ModelForm):
                    raise TypeError(
                        f"'{cls.__name__}.form_class' must be a "
                        f"subclass of 'ModelForm', not '{form_class.__name__}'"
                    )
                # form_class' model must match the model's class
                elif model and model != form_class.Meta.model:
                    raise TypeError(
                        f"'{cls.__name__}.form_class.model' must match "
                        f"'{cls.__name__}.model' class, if provided. "
                        f"({form_class.Meta.model.__name__} != {model.__name__})"
                    )
            else:
                form_class = modelform_factory(
                    model=cls.__dict__["model"], fields=cls.__dict__["fields"]
                )
                cls.form_class = form_class
            # So the new class *in any case* has a form_class
        super().__init_subclass__(**kwargs)

    # def __init__(self, *args, **kwargs):
    #     if not self.model:
    #         self.model = self.get_form_class().Meta.model
    #     super().__init__(*args, **kwargs)

    def get_form_class(self) -> type[forms.ModelForm]:
        """Returns the form class to use in this component."""

        # if there is an explicit form_class defined, use it
        if self.form_class:
            return self.form_class
        else:
            raise ImproperlyConfigured(
                f"'{self.__class__.__name__}' must either define 'form_class' "
                "or both 'model' and 'fields', or override 'get_form_class()'"
            )

    def get_model(self):
        """Returns the model class reliably."""
        if self.model:
            return self.model

        form_class = self.get_form_class()
        model = getattr(getattr(form_class, "_meta", None), "model", None)
        if model:
            self.model = model
            return self.model

        raise ImproperlyConfigured(
            f"{self.__class__.__name__} could not resolve model. "
            "Ensure 'form_class' defines a proper ModelForm with Meta.model, "
            "or set 'self.model' manually."
        )

    def _pre_load(self, object: models.Model = None, *args, **kwargs) -> None:
        """
        Automatically makes the object available in the component's attributes.

        Attributes:
            object (models.Model): the object to load into the component
        """
        if object:
            assert isinstance(object, self.get_model()), (
                self.__class__.__name__
                + " expects an instance of "
                + self.get_model().__name__
            )
        self.object = object or self.get_model()()
        self._copy_object_to_attrs()
        self._set_attrs_from_form_class_initial()

    def __setattr__(self, key, value):
        """Additionally to setting the component attribute, set it on the attached
        object, if applicable."""
        super().__setattr__(key, value)
        if self.object and key in {f.attname for f in self.object._meta.fields}:
            # if the key is a field of the 'self.object' model, set it on self.object
            setattr(self.object, key, value)

    def _reset(self):
        # set an empty model instance and initialize it with defaults
        self.object = self.get_model()()
        super()._reset()

    def get_form_kwargs(self):
        """Adds self.object as instance to the form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def _copy_object_to_attrs(self):
        """Copies all object attributes to the component props."""
        for name in {f.attname for f in self.object._meta.fields}:
            # FIXME: this recursively sets self.object.<attname> again:
            setattr(self, name, getattr(self.object, name))

    def get_form(self, data=None, files=None, **kwargs):
        """Returns a form, bound to given model instance."""
        # create an instance of model() and copy component's attributes to it
        instance = self.object
        for field_name, field in self.get_form_class().base_fields.items():
            # print(f"set {field_name} to {getattr(self, field_name)}")
            if isinstance(field, ModelChoiceField):
                setattr(instance, f"{field_name}_id", getattr(self, field_name))
            else:
                setattr(instance, field_name, getattr(self, field_name))

        return super().get_form()

    # def _get_context_object_name(self, is_list=False):
    #     """
    #     Returns a descriptive name to use in the context in addition to the
    #     default 'object'/'object_list'.
    #     """
    #     if self._context_object_name is not None:
    #         return self._context_object_name
    #
    #     elif self.object is not None:
    #         return (
    #             f"{self.object.__name__.lower()}_list"
    #             if is_list
    #             else self.object.__name__.lower()
    #         )

    def form_valid(self, form: ModelForm) -> None:
        """Overrides the form_valid method to save the ModelForm data to the
        database.

        Override This method if you need custom functionality."""
        self.object = form.save(commit=True)
        # FIXME: reset is not always wanted, only in Create, not Update
        self._reset()


class DynamicFormMixin:
    """
    A mixin class that provides functionality for dynamically updating fields'
    attributes, based on other fields or circumstances.

    This class checks for the existence of special methods in your component,
    and calls them to get the current `queryset`, `choices`, `hidden`, `disabled`,
    and `required` status for the corresponding field.

    Usage:
        Create a method that is called whenever a parent field changes its value, using
        the `@public.watch("field_name")` decorator. The method itself could be
        empty. It is just needed as trigger to rerender the form.

        ```python


        @public.watch("make")
        def make_changed(self, value, old_value, attr) -> None:
            pass

        def get_engine_hidden(self) -> bool:
            # hide engine_type if make is Tesla
            return self.make == Make.objects.get(name="Tesla")
        ```

    The following methods can be optionally defined in your component, and will get
    called in time to determine the fields' attributes before rendering.

    Methods:
        get_<field_name>_queryset(): Returns the current queryset for the given field.
        get_<field_name>_disabled(): whether the given field should be
            disabled, depending on the values of other fields.
        get_<field_name>_hidden(): returns whether the given field should be
            hidden, depending on the values of other fields.
        get_<field_name>_required(): returns whether the given field is
            required, depending on the values of other fields.

        All these methods are normal instance methods and must return a boolean value.
    """

    def get_form(self, *args, **kwargs):
        """Updates dynamic fields when the form is created."""

        # get form and modify fields according to saved field state
        form = super().get_form(*args, **kwargs)
        # parents = self.field_dependencies.values()
        for field_name, field in form.fields.items():

            if update_method := getattr(self, f"get_{field_name}_disabled", None):
                form.fields[field_name].disabled = update_method()

            if update_method := getattr(self, f"get_{field_name}_hidden", None):
                form.fields[field_name].widget.attrs["hidden"] = update_method()

            if update_method := getattr(self, f"get_{field_name}_required", None):
                form.fields[field_name].required = update_method()

            # check if there is a dynamic queryset
            if update_method := getattr(self, f"get_{field_name}_queryset", None):
                form.fields[field_name].queryset = update_method()

            # check if there are dynamic choices
            if update_method := getattr(self, f"get_{field_name}_choices", None):
                form.fields[field_name].choices = update_method()
        return form


# this is just experimental
# class WizardFormComponent(FormComponent):
#     __abstract__ = True
