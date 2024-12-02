import logging
import importlib
import os
from copy import copy
from typing import Optional, Self, Any
from types import FunctionType
from enum import Enum
import inspect
import re
import itertools
import uuid
from weakref import WeakKeyDictionary
from functools import wraps
from threading import local

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import QuerySet
from django.forms import Form, modelform_factory, BaseForm, FileField
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
from django.http import JsonResponse, HttpRequest
from django.urls import reverse

from ..exceptions import ComponentError
from ..utils import camel_case_to_underscore, to_json, TetraJSONEncoder, isclassmethod
from ..state import encode_component, decode_component, skip_check
from ..templates import InlineOrigin, InlineTemplate

from .callbacks import CallbackList


thread_local = local()

logger = logging.getLogger(__name__)


def make_template(cls) -> Template:
    """Create a template from a component class.

    Uses either the `cls.template` attribute as inline template string,
    or the html template file source in the component's directory. If both are defined,
    'template' overrides 'template_name'.
    """
    from ..templatetags.tetra import get_nodes_by_type_deep

    # if only "template" is defined, use it as inline template string.
    if hasattr(cls, "template"):
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
                "{% load tetra %}" + cls.template,
                origin=origin,
            )
        except TemplateSyntaxError:
            # By default, we want to compile templates during python compile time,
            # however, the template exceptions are much better when raised at runtime
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
                        "{% load tetra %}" + cls.template,
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
        # Here we definitely are in a dir-style component

        # try to find <component_name>.html within component's directory
        module = importlib.import_module(cls.__module__)
        if not hasattr(module, "__path__"):
            raise ComponentError(
                f"Component module '{cls.__module__}' seems not to be a component."
            )
        component_name = module.__name__.split(".")[-1]
        module_path = module.__path__[0]
        # if path is a file, get the containing directory
        # template_dir = os.path.dirname(module_path)

        template_file_name = f"{component_name}.html"
        # Load the template using a custom loader
        from django.template.loaders.filesystem import Loader as FileSystemLoader

        try:
            engine = Engine(dirs=[module_path], app_dirs=False)
            loader = FileSystemLoader(engine)
            for template_path in loader.get_template_sources(template_file_name):
                try:
                    # Open and read the template source
                    with open(template_path.name, "r", encoding="utf-8") as f:
                        template_source = f.read()

                    origin = InlineOrigin(
                        name=os.path.join(module_path, template_file_name),
                        template_name=template_file_name,
                        start_line=0,
                        component=cls,
                    )
                    # Compile the template
                    template = Template(template_source, origin, template_file_name)
                    break
                except FileNotFoundError:
                    # If the file is not found, continue with the next source
                    continue
            else:
                # If no template is found, raise an error
                raise ComponentError(
                    f"Template file '{template_file_name}' not found for component"
                    f" '{cls.__name__}'."
                )
            # template = get_template(template_file_name).template
        except TemplateDoesNotExist:
            raise ComponentError(
                f"Template file '{template_file_name}' not found for component"
                f" '{cls.__name__}'."
            )
    return template


class BasicComponentMetaClass(type):
    def __new__(mcls, name, bases, attrs):
        newcls = super().__new__(mcls, name, bases, attrs)
        newcls._name = camel_case_to_underscore(newcls.__name__)
        if "__abstract__" not in attrs or attrs["__abstract__"] is False:
            newcls._template = make_template(newcls)
        return newcls


class RenderData(Enum):
    INIT = 0
    MAINTAIN = 1
    UPDATE = 2


class BasicComponent(metaclass=BasicComponentMetaClass):
    __abstract__ = True
    style: Optional[str] = None
    _name = None
    _library = None
    _app = None
    _leaded_from_state = False

    def __init__(
        self,
        _request,
        _attrs: dict = None,
        _context: dict | RequestContext = None,
        _blocks=None,
        *args,
        **kwargs,
    ) -> None:
        self.request = _request
        self.attrs = _attrs
        self._context = _context
        self._blocks = _blocks
        self._call_load(*args, **kwargs)

    @classmethod
    def full_component_name(cls) -> str:
        return f"{cls._library.app.label}__{cls._library.name}__{cls._name}"

    @classmethod
    def get_source_location(cls) -> tuple[str, int, int]:
        filename = inspect.getsourcefile(cls)
        lines, start = inspect.getsourcelines(cls)
        return filename, start, len(lines)

    @classmethod
    def get_template_source_location(cls) -> tuple[str, int | None]:
        filename, comp_start, com_end = cls.get_source_location()
        if not hasattr(cls, "template") or not cls.template:
            return filename, None
        with open(filename, "r") as f:
            source = f.read()
        start = source.index(cls.template)
        line = source[:start].count("\n") + 1
        return filename, line

    @classmethod
    def _get_component_file_path_with_extension(cls, extension):
        if hasattr(cls, "template") and cls.template:
            # assume this is an inline component, no css/js files available
            return ""
        module = importlib.import_module(cls.__module__)
        component_name = module.__name__.split(".")[-1]
        module_path = module.__path__[0]
        file_name = f"{component_name}.{extension}"
        return os.path.join(module_path, file_name)

    @classmethod
    def _read_component_file_with_extension(cls, extension):
        file_path = cls._get_component_file_path_with_extension(extension)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    return f.read()
            except FileNotFoundError:
                return ""
        else:
            return ""

    @classmethod
    def has_script(cls) -> bool:
        return False

    @classmethod
    def make_script(cls, component_var=None) -> str:
        """In BasicComponent, always returns an empty string."""
        return ""

    @classmethod
    def has_styles(cls) -> bool:
        if bool(hasattr(cls, "style") and cls.style):
            return True
        else:
            return os.path.exists(cls._get_component_file_path_with_extension("css"))

    @classmethod
    def make_styles(cls) -> str:
        # check if the style is defined in the class otherwise check if there is a file in the component directory
        if bool(hasattr(cls, "style") and cls.style):
            return cls.style
        else:
            return cls._read_component_file_with_extension("css")

    @classmethod
    def make_styles_file(cls) -> str:
        # check if we have a style defined in the class otherwise check if there is a file in the component directory
        if bool(hasattr(cls, "style") and cls.style):
            filename, comp_start_line, source_len = cls.get_source_location()
            with open(filename, "r") as f:
                py_source = f.read()
            comp_start_offset = len("\n".join(py_source.split("\n")[:comp_start_line]))
            start = py_source.index(cls.style, comp_start_offset)
            before = py_source[:start]
            before = re.sub(r"\S", " ", before)
            return f"{before}{cls.style}", True
        else:
            return cls._read_component_file_with_extension("css"), False

    @classmethod
    def as_tag(cls, _request, *args, **kwargs) -> SafeString:
        if not hasattr(_request, "tetra_components_used"):
            _request.tetra_components_used = set()
        _request.tetra_components_used.add(cls)
        component = cls(_request, *args, **kwargs)
        component.ready()
        return component.render()

    def _call_load(self, *args, **kwargs) -> None:
        self.load(*args, **kwargs)

    def load(self, *args, **kwargs) -> None:
        """Override this method to load the component's data, e.g. from the database.

        Caution: Any attributes that are set in this method are NOT saved with the
        state, for efficiency.
        """
        pass

    def _add_self_attrs_to_context(self, context) -> None:
        for key in dir(self):
            if not (key.startswith("_") or isclassmethod(getattr(self, key))):
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

    def render(self) -> SafeString:
        context = self.get_context_data()

        with context.render_context.push_state(self._template, isolated_context=True):
            if self._blocks:
                if BLOCK_CONTEXT_KEY not in context.render_context:
                    context.render_context[BLOCK_CONTEXT_KEY] = BlockContext()
                block_context = context.render_context[BLOCK_CONTEXT_KEY]
                block_context.add_blocks(self._blocks)

            if context.template is None:
                with context.bind_template(self._template):
                    html = self._template._render(context)
            else:
                html = self._template._render(context)

        return mark_safe(html)

    def ready(self):
        """Hook method when component is fully loaded and ready to render.

        You can use this method to do additional initialization logic.
        Attributes that are set here override attributes set in `load()` or the ones
        recovered from the state, or frontend data.
        """


empty = object()


class PublicMeta(type):
    def __getattr__(self, name):
        if hasattr(self, f"do_{name}"):
            inst = self()
            return getattr(inst, f"do_{name}")
        else:
            raise AttributeError(f"Public decorator has no method {name}.")


class Public(metaclass=PublicMeta):
    def __init__(self, obj=None, update=True) -> None:
        self._update = update
        self._watch = []
        self._debounce = None
        self._debounce_immediate = None
        self._throttle = None
        self._throttle_trailing = None
        self._throttle_leading = None
        self.__call__(obj)

    def __call__(self, obj) -> Self:
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
            self.obj = obj.obj if obj.obj else self.obj

        elif self._update and isinstance(obj, FunctionType):

            @wraps(obj)
            def fn(self, *args, **kwargs):
                ret = obj(self, *args, **kwargs)
                self.update()
                return ret

            self.obj = fn
        else:
            self.obj = obj
        return self

    def __getattr__(self, name) -> Any:
        if hasattr(self, f"do_{name}"):
            return getattr(self, f"do_{name}")
        else:
            raise AttributeError(f"Public decorator has no method {name}.")

    def do_watch(self, *args) -> Self:
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


public = Public


tracing_component_load = WeakKeyDictionary()


class ComponentMetaClass(BasicComponentMetaClass):
    def __new__(mcls, name, bases, attrs):
        public_methods = list(
            itertools.chain.from_iterable(
                base._public_methods
                for base in bases
                if hasattr(base, "_public_methods")
            )
        )
        public_properties = list(
            itertools.chain.from_iterable(
                base._public_properties
                for base in bases
                if hasattr(base, "_public_properties")
            )
        )
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, Public):
                attrs[attr_name] = attr_value.obj
                if isinstance(attrs[attr_name], FunctionType):
                    pub_met = {"name": attr_name}
                    if attr_value._watch:
                        pub_met["watch"] = attr_value._watch
                    if attr_value._debounce:
                        pub_met["debounce"] = attr_value._debounce
                        pub_met["debounce_immediate"] = attr_value._debounce_immediate
                    if attr_value._throttle:
                        pub_met["throttle"] = attr_value._throttle
                        pub_met["throttle_trailing"] = attr_value._throttle_trailing
                        pub_met["throttle_leading"] = attr_value._throttle_leading
                    public_methods.append(pub_met)
                else:
                    public_properties.append(attr_name)
        newcls = super().__new__(mcls, name, bases, attrs)
        newcls._public_methods = public_methods
        newcls._public_properties = public_properties
        return newcls


class Component(BasicComponent, metaclass=ComponentMetaClass):
    __abstract__ = True
    script: Optional[str] = None
    _callback_queue = None
    _excluded_props_from_saved_state = [
        "request",
        "_callback_queue",
        "_loaded_children_state",
        "_excluded_load_props_from_saved_state",
        "_leaded_from_state",
        "_leaded_from_state_data",
    ]
    _excluded_load_props_from_saved_state = []
    _loaded_children_state = None
    _load_args = []
    _load_kwargs = {}
    key = public(None)

    def __init__(self, _request, key=None, *args, **kwargs) -> None:
        super().__init__(_request, *args, **kwargs)
        self.key = key if key is not None else self.full_component_name()

    @classmethod
    def from_state(
        cls,
        data: dict,
        request: HttpRequest,
        key: str = None,
        _attrs=None,
        _context=None,
        _blocks=None,
        *args,
        **kwargs,
    ) -> Any:
        """Creates and initializes a component instance from its serialized state."""
        if not (
            isinstance(data, dict)
            and "state" in data
            and isinstance(data["state"], str)
            and "data" in data
            and isinstance(data["data"], dict)
        ):
            raise TypeError("Invalid State value.")

        component = decode_component(data["state"], request)
        if not isinstance(component, cls):
            raise TypeError(
                f"Component '{component.__class__.__name__}' of invalid "
                f"type, should be: {cls.__name__}."
            )

        component.request = request
        if key:
            component.key = key
        if _attrs:
            component.attrs = _attrs
        if _context:
            component._context = _context
        if _blocks:
            component._blocks = _blocks
        if len(args) > 0:
            component._load_args = args
        if len(kwargs) > 0:
            component._load_kwargs = kwargs
        component._recall_load()

        for key, value in data["data"].items():
            setattr(component, key, value)
        component._leaded_from_state = True
        component._leaded_from_state_data = data["data"]
        component.ready()
        return component

    @classmethod
    def has_script(cls) -> bool:
        """Returns True if the component has a javascript script, else False."""
        # check if the script is defined in the class otherwise check if there is a file in the component directory
        if bool(hasattr(cls, "script") and cls.script):
            return True
        else:
            return os.path.exists(cls._get_component_file_path_with_extension("js"))

    @classmethod
    def _component_url(cls, method_name) -> str:
        return reverse(
            "tetra_public_component_method",
            args=[cls._library.app.label, cls._library.name, cls._name, method_name],
        )

    @classmethod
    def make_script(cls, component_var=None) -> str:
        """This method generates a JavaScript script for the component.
        It includes the component's methods, attributes, and server-side methods.
        This script can be imported dynamically via Alpine.init() and used to update
        the component's state
        """
        component_server_methods = []
        for method in cls._public_methods:
            method_data = copy(method)
            method_data["endpoint"] = (cls._component_url(method["name"]),)
            component_server_methods.append(method_data)

        component_server_methods.append(
            {
                # TODO: security & efficiency: only append _upload_temp_file if
                #  necessary, e.g. file field present.
                "name": "_upload_temp_file",
                "endpoint": cls._component_url("_upload_temp_file"),
            }
        )
        if not component_var:
            component_var = cls.script if cls.has_script() else "{}"
        return render_to_string(
            "script.js",
            {
                "component_name": cls.full_component_name(),
                "component_script": component_var,
                "component_server_methods": to_json(component_server_methods),
                "component_server_properties": to_json(cls._public_properties),
            },
        )

    @classmethod
    def make_script_file(cls) -> str:
        if bool(hasattr(cls, "script") and cls.script):
            filename, comp_start_line, source_len = cls.get_source_location()
            with open(filename, "r") as f:
                py_source = f.read()
            comp_start_offset = len("\n".join(py_source.split("\n")[:comp_start_line]))
            start = py_source.index(cls.script, comp_start_offset)
            before = py_source[:start]
            before = re.sub(r"\S", " ", before)
            return f"{before}{cls.script}", True
        else:
            # Find script in the component's directory
            return cls._read_component_file_with_extension("js"), False

    def _call_load(self, *args, **kwargs) -> None:
        """Load the component's state and attributes.
        It keeps a record of the given parameters for later recalls and
        then calls the (user defined) load method of the component.
        """
        self._load_args = args
        self._load_kwargs = kwargs
        # prevent properties set in load() to be save with the state
        tracing_component_load[self] = set()
        try:
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
            tracing_component_load[self].add(item)
        return super().__setattr__(item, value)

    @property
    def client(self) -> CallbackList:
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
        self._load_args = load_args

    def _data(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in self._public_properties}

    def _encoded_state(self) -> str:
        return encode_component(self)

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        for key in (
            self._excluded_props_from_saved_state
            + self._excluded_load_props_from_saved_state
        ):
            if key in state:
                del state[key]
        return state

    def _render_data(self) -> dict[str, Any]:
        """Returns a dictionary that includes the component's attributes and a
        special attribute __state that contains the component's encoded state as a JSON
        string.
        This dictionary is used to render the component's HTML.
        """
        data = self._data()
        data["__state"] = self._encoded_state()
        return data

    def _add_self_attrs_to_context(self, context) -> None:
        super()._add_self_attrs_to_context(context)
        if hasattr(self, "_loaded_children_state") and self._loaded_children_state:
            children_state = {c["data"]["key"]: c for c in self._loaded_children_state}
            context["_loaded_children_state"] = children_state
        else:
            context["_loaded_children_state"] = None

    def render(self, data=RenderData.INIT) -> SafeString:
        """Renders the component's HTML."""
        if hasattr(thread_local, "_tetra_render_data"):
            data = thread_local._tetra_render_data
            set_thread_local = False
        else:
            thread_local._tetra_render_data = data
            set_thread_local = True
        html = super().render()
        if set_thread_local:
            del thread_local._tetra_render_data
        tag_name = re.match(r"^\s*<\w+", html)
        if not tag_name:
            raise ComponentError(
                f"Error in {self.__class__.__name__}: The component's template is "
                "not enclosed in HTML tags."
            )
        tag_name_end = tag_name.end(0)

        extra_tags = [
            f'tetra-component="{self.full_component_name()}"',
            'x-bind="__rootBind"',
        ]
        if self.key:
            extra_tags.append(f'key="{self.key}"')
        if data == RenderData.UPDATE and self._leaded_from_state:
            data_json = escape(to_json(self._render_data()))
            old_data_json = escape(to_json(self._leaded_from_state_data))
            extra_tags.append('x-data=""')
            extra_tags.append(f'x-data-update="{data_json}"')
            extra_tags.append(f'x-data-update-old="{old_data_json}"')
        elif data == RenderData.MAINTAIN:
            extra_tags.append('x-data=""')
            extra_tags.append("x-data-maintain")
        else:
            data_json = escapejs(to_json(self._render_data()))
            extra_tags.append(f"x-data=\"{self.full_component_name()}('{data_json}')\"")
        html = f'{html[:tag_name_end]} {" ".join(extra_tags)} {html[tag_name_end:]}'
        return mark_safe(html)

    def update_html(self, include_state=False) -> None:
        """Updates the component's HTML.

        If `include_state` is True, it includes the component's state in the HTML.
        Otherwise, it only includes the component's attributes.
        """
        if include_state:
            self.client._updateHtml(self.render(data=RenderData.UPDATE))
        else:
            self.client._updateHtml(self.render(data=RenderData.MAINTAIN))

    def update_data(self) -> None:
        """Updates the component's state with the latest data from the server."""
        self.client._updateData(self._render_data())

    def update(self) -> None:
        """Updates the component's HTML and state."""
        self.update_html(include_state=True)

    def replace_component(self) -> None:
        """Replaces the current component with a new one. It first updates the HTML
        and state of the current component, and then it creates a new component with
        the same name and attributes as the current component.
        """
        self.client._replaceComponent(self.render())

    def push_url(self, url: str) -> None:
        """Pushes a new URL to the browser's history."""
        self.client._pushUrl(url)

    def replace_url(self, url: str) -> None:
        """Replaces the current URL with a new one."""
        self.client._pushUrl(url, replace=True)

    def _call_public_method(
        self, request, method_name, children_state, *args
    ) -> JsonResponse:
        self._loaded_children_state = children_state
        self._callback_queue = CallbackList()
        result = getattr(self, method_name)(*args)
        callbacks = self._callback_queue.serialize()
        self._callback_queue = None
        libs = list(
            set(component._library for component in request.tetra_components_used)
        )
        # TODO: error handling
        return JsonResponse(
            {
                "styles": [lib.styles_url for lib in libs],
                "js": [lib.js_url for lib in libs],
                "success": True,
                "result": result,
                "callbacks": callbacks,
            },
            encoder=TetraJSONEncoder,
        )

    @public
    def _refresh(self) -> None:
        """Re-render and return
        This is just a noop as the @public decorator implements this functionality
        """
        pass


class FormComponentMetaClass(ComponentMetaClass):
    def __new__(cls, name, bases, dct):
        # iter through form fields, and set a public attribute to the component
        # for each field

        form_class = dct.get("form_class", None)

        if form_class:
            for field_name in form_class.base_fields:
                dct[field_name] = public(form_class.base_fields[field_name].initial)
        return super().__new__(cls, name, bases, dct)


class FormComponent(Component, metaclass=FormComponentMetaClass):
    """
    Component that can render a form, and validate it.

    Attributes:
        form_class (type(BaseForm)):
            The form class to use for this component. All fields of the form are
            dynamically created as public attributes in the component,
            and initialized with the form's fields' initial values.
    """

    __abstract__ = True
    form_class: type(forms.BaseForm) = None
    form_submitted: bool = False
    form_errors: dict = {}  # TODO: make protected + include in render context
    form_temp_files: dict = {}

    _form: Form = None

    def ready(self):
        self._form = self.get_form(self._data())

    def render(self, data=RenderData.INIT) -> SafeString:
        # Don't show form errors if form is not submitted yet
        if not self.form_submitted:
            self._form.errors.clear()
        return super().render(data=data)

    def get_context_data(self, **kwargs) -> RequestContext:
        context = super().get_context_data(**kwargs)
        context["form"] = self._form
        return context

    def get_form_class(self):
        """Returns the form class to use in this component."""
        return self.form_class

    def get_form(self, data=None, files=None, **kwargs):
        """Returns a new form instance, initialized with data from the component
        attributes."""
        if data is None:
            data = self._data()

        cls = self.get_form_class()
        form = cls(data=data, files=files, **kwargs)
        self._add_alpine_models_to_fields(form)
        return form

    def _add_alpine_models_to_fields(self, form) -> None:
        """Connects the form's fields to the Tetra backend using x-model attributes."""
        for field_name, field in form.fields.items():
            if field_name in self._public_properties:
                if isinstance(field, FileField):
                    form.fields[field_name].widget.attrs.update(
                        {"@change": "_uploadFile"}
                    )
                    if hasattr(field, "temp_file"):
                        # TODO: Check if we need to send back the temp file name and which attribute to use, might not be necessary
                        form.fields[field_name].widget.attrs.update(
                            {"data-tetra-temp-file": field.temp_file}
                        )
                else:
                    # form.fields[field_name].initial = getattr(self, field_name)
                    form.fields[field_name].widget.attrs.update({"x-model": field_name})

    @public
    def validate(self) -> None:
        """Validates the data using the form defined in `form_class`, and re-renders
        the component, without saving the form."""
        if self._form.is_valid():
            pass
        else:
            self.form_errors = self._form.errors.get_json_data(escape_html=True)
            # set the possibly cleaned values back to the component's attributes
            for attr, value in self._form.cleaned_data.items():
                setattr(self, attr, value)

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

    @public
    def submit(self) -> None:
        """Submits the form.

        The component will validate the data against the form, and if the form is valid,
        it will call form_valid(), else form_invalid().
        """

        # find all temporary files in the form and read them and write to the form fields
        for field_name, file_details in self.form_temp_files.items():
            if file_details:
                storage = (
                    self._form.fields[field_name].storage
                    if hasattr(self._form.fields[field_name], "storage")
                    else default_storage
                )
                with storage.open(file_details["temp_name"], "rb") as file:
                    storage.save(file_details["original_name"], file)
                # TODO: Add error checking and double check the form value is being set correctly
                storage.delete(file_details["temp_name"])
                self._form.fields[field_name].initial = file_details["original_name"]

        self.form_submitted = True

        if self._form.is_valid():
            self.form_valid(self._form)
        else:
            self.form_errors = self._form.errors.get_json_data(escape_html=True)
            # set the possibly cleaned values back to the component's attributes
            for attr, value in self._form.cleaned_data.items():
                if type(value) in skip_check:
                    setattr(self, attr, value)
                else:
                    setattr(self, attr, TetraJSONEncoder().default(value))
            self.form_invalid(self._form)

    @public
    def _upload_temp_file(self, form_field, original_name, file) -> str | None:
        """Uploads a file to the server temporarily."""
        # TODO: Add validation
        if (
            file
            and form_field in self._form.fields
            and isinstance(self._form.fields[form_field], FileField)
        ):
            temp_file_name = f"tetra_temp_upload/{uuid.uuid4()}"
            storage = (
                self._form.fields[form_field].storage
                if hasattr(self._form.fields[form_field], "storage")
                else default_storage
            )
            storage.save(temp_file_name, file)
            # TODO: Add error checking, double check this - it seems like we need call setattr as well as setting directly?
            self.form_temp_files[form_field] = dict(
                temp_name=temp_file_name, original_name=original_name
            )
            setattr(self, self.form_temp_files[form_field]["temp_name"], temp_file_name)
            setattr(
                self, self.form_temp_files[form_field]["original_name"], original_name
            )
            return temp_file_name
        return None

    def clear(self):
        """Clears the form data (sets all values to defaults) and renders the
        component."""
        for attr in self._public_properties:
            setattr(self, attr, getattr(self.__class__, attr))


class ModelFormComponent(FormComponent):
    __abstract__ = True
    form_class: type(forms.ModelForm) = None
    model: type(models.Model) = None
    fields: list[str] = "__all__"

    def get_form_class(self):
        """Returns the form class to use in this component."""
        if self.form_class:
            return self.form_class
        if self.model:
            return modelform_factory(model=self.model, fields=self.fields)
        raise ImproperlyConfigured(
            f"'{self.__class__.__name__}' must either define 'form_class' "
            "or 'model', or override 'get_form_class()'"
        )

    def form_valid(self, form) -> None:
        """Overrides the form_valid method to save the ModelForm data to the
        database.

        Override This method if you need custom functionality."""
        form.save()


class DependencyFormMixin:
    """
    A mixin class that provides functionality for updating dependent fields based on
    parent fields in Tetra components

    This class uses a declarative dependency dictionary (`field_dependencies`) to
    define the relationship between child and parent fields, and some helper methods
    to update child fields based on parent field changes.

    Usage:
        Inherit a FormComponent from this class, and add field_dependencies to it.
        You should now call `self.update_dependent_fields` method whenever a parent
        field changes its value, using the `@public.watch("field_name")` decorator:

        ```python
        field_dependencies = {"model": "make"}

        @þublic.watch("make")
        def make_changed(self, value, old_value, attr) -> None:
            self.update_field_queryset("model", CarModel.objects.filter(make=value))

            # hide engine_type if make is Tesla
            if value == Make.objects.get(name="Tesla")
                self._form.fields["engine_type"].visible = True
        ```

        It is possible that you call this method in `load()` too, if you e.g. prefill
        the parent field and want to have its dependent fields updated accordingly.

    Attributes:
        field_dependencies: A dictionary that maps child field names to their
        corresponding parent. The dict keys are the child field names, and the dict
        values are the parents that they depend on.
        Examples:
            field_dependencies = {
              "model": "make",  # model depends on make
              "year": "make"  # year depends on make
            }

    """

    field_dependencies: dict[str, str | tuple] = {}

    def __init__(self, *args, **kwargs):
        if not self.field_dependencies:
            raise AttributeError(
                f"{self.__class__.__name__} needs a 'field_dependencies' attribute."
            )
        super().__init__(*args, **kwargs)

    def get_form(self, *args, **kwargs):
        """Updates querysets of dependent fields when the form is created."""
        form = super().get_form(*args, **kwargs)
        for field_name, parent_name in self.field_dependencies.items():
            if getattr(self, parent_name, None):
                get_queryset = getattr(self, f"get_{field_name}_queryset", None)
                if get_queryset:
                    form.fields[field_name].queryset = get_queryset()
        return form

    # def _get_queryset_for_field(self, field_name: str) -> QuerySet:
    #     """Returns the queryset for the given field."""
    #     parent_name = self.field_dependencies.get(field_name)
    #     if parent_name:
    #         parent_value = getattr(self, parent_name, None)
    #         if parent_value:
    #             return self.model._default_manager.filter(**{parent_name: parent_value})
    #     return self.model._default_manager.none()

    def update_field_queryset(
        self,
        child_field_name: str,
        queryset: QuerySet,
        old_value: Any = None,
    ):
        """Helper method that updates the queryset of the child field based on the
        value of its parent field.

        If the parent field value changes, the child field's queryset is updated
        accordingly.
        """
        if not child_field_name:
            return
        parent_field_name = self.field_dependencies[child_field_name]
        parent_value = getattr(self, parent_field_name, None)
        if not parent_value:
            # if parent is not available/set, always empty child's queryset
            self._form.fields[child_field_name].queryset = queryset.none()
            setattr(self, child_field_name, None)
            print(f"Set {child_field_name} to None")
            return

        # clear children field's errors and value ONLY if parent value has changed
        # if old_value and parent_value != old_value:
        #     setattr(self, child_field_name, None)
        #     print(f"reset {child_field_name} to None")
        #     errors = self._form.errors.get(child_field_name, None)
        #     if errors:
        #         print(f"clean form errors for {child_field_name}: {errors}")
        #         # errors.clear()
        self._form.fields[child_field_name].queryset = queryset

        def set_field_visibility(self, field_name: str, visible: bool):
            """Helper method to set the visibility of a field in the form."""
            self._form.fields[field_name].visible = visible


class GenericObjectFormComponent(ModelFormComponent):
    """
    Component that can render a Model object using a ModelForm, load and
    save the given object, and validate it. This is basically the equivalent of the
    UpdateView/CreateView class for views in Django.

    Attributes:
        form_class (type(ModelForm)): the ModelForm class to use
        _fields (list[str]): the fields to use in the form
        _context_object_name (str): the name of the context object in the template (TODO)
    """

    __abstract__ = True
    object: models.Model = None
    _fields: list[str] = []
    _context_object_name = None  # TODO

    def get_form_class(self):
        """Returns the form class to use in this component."""

        if self.form_class is not None:
            return self.form_class

        if self.object is not None and self._fields is not None:
            return forms.modelform_factory(self.object._meta.model, fields=self._fields)

        raise ImproperlyConfigured(
            f"'{self.__class__.__name__}' must either define 'form_class' "
            "or both 'object' and '_fields', or override 'get_form_class()'"
        )

    def load(self, object: models.Model, *args, **kwargs) -> None:
        self.object = object
        self._reset()
        super().load(*args, **kwargs)

    def get_form(self, data=None, files=None, **kwargs):
        """Returns a form, bound to given model instance."""
        return super().get_form(data=data, files=files, instance=self.object, **kwargs)

    # def get_context_data(self, **kwargs):
    #     """Insert the form into the context dict."""
    #     if "form" not in kwargs:
    #         kwargs["form"] = self.get_form()
    #     return super().get_context_data(**kwargs)

    def _get_context_object_name(self, is_list=False):
        """
        Returns a descriptive name to use in the context in addition to the
        default 'object'/'object_list'.
        """
        if self._context_object_name is not None:
            return self._context_object_name

        elif self.object is not None:
            return (
                f"{self.object.__name__.lower()}_list"
                if is_list
                else self.object.__name__.lower()
            )

    def _reset(self):
        """Resets all form fields. This internal method is not exposed as a public
        API and can be called by load() too."""
        for field in self.get_form_class().base_fields:
            if hasattr(self.object, field):
                setattr(self, field, getattr(self.object, field))
                # FIXME: does not work yet? include non-object fields like new_password1

    @public
    def reset(self):
        """Convenience method to be called by the frontend to reset the form.

        All values will be reset to the initial object values.
        """
        self._reset()

    def form_valid(self, form) -> None:
        self.object = form.save()
