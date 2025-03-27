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
from weakref import WeakKeyDictionary
from functools import wraps
from threading import local

from django import forms
from django.core.exceptions import ImproperlyConfigured
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
from django.http import JsonResponse, HttpRequest
from django.urls import reverse
from django.template.loaders.filesystem import Loader as FileSystemLoader

from ..exceptions import ComponentError
from ..middleware import TetraHttpRequest
from ..utils import (
    camel_case_to_underscore,
    to_json,
    TetraJSONEncoder,
    isclassmethod,
    TetraTemporaryUploadedFile,
)
from ..state import encode_component, decode_component
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
        except TemplateSyntaxError as e:
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

    elif hasattr(cls, "template_name"):
        raise NotImplementedError(
            f"'template_name' is not implemented yet for Tetra components ({cls})"
        )
        # template_file_name = cls.template_name
        # template_dir = os.path.dirname(template_file_name)

    else:

        # try to find <component_name>.html within component's directory
        module = importlib.import_module(cls.__module__)

        # No template, no template_name attrs found
        # Here we definitely must have a dir-style component
        if not hasattr(module, "__path__"):
            raise ComponentError(
                f"'{cls.__module__}' is not a valid component library of component "
                f"'{cls.__name__}'."
            )
        module_path = module.__path__[0]
        component_name = module.__name__.split(".")[-1]
        # if path is a file, get the containing directory
        # template_dir = os.path.dirname(module_path)

        # FIXME: better use cls.get_template_source_location() for this!
        # template_source = cls._read_component_file_with_extension("html")

        template_file_name = f"{component_name}.html"

        # Load the template using a custom loader
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
                    template = Template(
                        "{% load tetra %}" + template_source, origin, template_file_name
                    )
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
        _request: TetraHttpRequest | HttpRequest,
        _attrs: dict = None,
        _context: dict | RequestContext = None,
        _blocks=None,
        *args,
        **kwargs,
    ) -> None:
        """Initializes the component with the provided attributes and context.

        It calls load() with the optional args/kwargs."""

        super().__init__()  # call init without kwargs.
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
        """Returns the filename line number, and line count of the component's source code."""
        filename = inspect.getsourcefile(cls)
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
    def make_styles_file(cls) -> tuple[str, bool]:
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

    def render(self) -> SafeString:
        self.recalculate_attrs(component_method_finished=True)
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

    def recalculate_attrs(self, component_method_finished: bool):
        """Code that should be run before and after user interactions with attributes.

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


class PublicMeta(type):
    def __getattr__(self, name):
        if hasattr(self, f"do_{name}"):
            inst = self()
            return getattr(inst, f"do_{name}")
        else:
            raise AttributeError(f"Public decorator has no method {name}.")


class Public(metaclass=PublicMeta):
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
        self._watch = []
        self._debounce = None
        self._debounce_immediate = None
        self._throttle = None
        self._throttle_trailing = None
        self._throttle_leading = None
        self._event_subscriptions = []
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
            self.obj = obj.obj if obj.obj else self.obj

        elif self._update and isinstance(obj, FunctionType):

            @wraps(obj)
            def fn(instance: "Component", *args, **kwargs):
                ret = obj(instance, *args, **kwargs)
                instance.update()
                return ret

            self.obj = fn
            # if we recorded that the method should subscribe to an event, mark it as such
            if self._event_subscriptions:
                self.obj._event_subscription = self._event_subscriptions
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

    def do_subscribe(self, event) -> Self:
        """Marks the method to subscribe to one or more Javascript event."""
        # we can't access the class whose method we are decorating directly,
        # so we store the event name as an attribute on the method, so the
        # Component class itself can check (in its MetaClass or later
        # __init_subclass__) which methods have a subscription.
        self._event_subscriptions.append(event)
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
        event_subscriptions: dict[str, str] = {}
        for attr_name, attr_value in attrs.items():

            if isinstance(attr_value, Public):
                # if there is public decorated attribute/method, replace it with the
                # attribute/method itself, as we don't need the decorator anymore.

                attrs[attr_name] = attr_value.obj

                if isinstance(attrs[attr_name], FunctionType):
                    # decorated object is a method
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
                    for event in attr_value._event_subscriptions:
                        # save {event_name:method_name} for each event
                        event_subscriptions.update({event: attr_value.obj.__name__})
                    public_methods.append(pub_met)
                else:
                    public_properties.append(attr_name)
        newcls = super().__new__(mcls, name, bases, attrs)
        newcls._public_methods = public_methods
        newcls._public_properties = public_properties
        newcls._event_subscriptions = event_subscriptions
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
        "_event_subscriptions",
        "__abstract__",
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
            attr_type = (
                component.__annotations__[key]
                if (key in component.__annotations__)
                else type(key)
            )
            # if client data type is a model, try to see the value in the
            # recovered data as Model.pk and get the model again.
            if issubclass(attr_type, Model) and attr_type is not type(value):
                if value:
                    # TODO: optimization: before hitting the DB another time (the
                    #  unpickling already did this), we could check if the pk
                    #  changed? If not, just keep the object.
                    value = attr_type.objects.get(pk=value)
                else:
                    value = None  # or attr_type.objects.none()
            setattr(component, key, value)
        component._leaded_from_state = True
        component._leaded_from_state_data = data["data"]
        component.recalculate_attrs(component_method_finished=False)
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
    def make_script_file(cls) -> tuple[str, bool]:
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
        tag_name = re.match(r"^\s*(<!--.*-->)?\s*<\w+", html)
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
        """Replaces the current component with a new one. It first creates a new
        component with the same name and attributes as the current component and
        inserts it into the DOM, and then removes the current component from the DOM.
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
            headers={"T-Response": "true"},
        )

    @public
    def _refresh(self) -> None:
        """Re-render and return
        This is just a noop as the @public decorator implements this functionality
        """
        pass


class FormComponentMetaClass(ComponentMetaClass):
    def __new__(cls, name, bases, dct):
        # iter through form fields if there is a static form_class, and set a public
        # attribute to the component for each field

        form_class = dct.get("form_class", None)
        dct.setdefault("__annotations__", {})

        if form_class:
            # logger.debug(
            #     f"Automatically creating component attributes from form fields for "
            #     f"class {name}"
            # )
            for field_name, field in form_class.base_fields.items():
                # try to read the type of the component attribute from the form field
                initial = field.to_python(field.initial or "")
                if isinstance(field, ModelChoiceField):
                    python_type = field.queryset.model
                else:
                    python_type = type(initial)

                # logger.debug(f"  {field_name} -> {python_type}")
                dct[field_name] = public(initial)
                dct["__annotations__"][field_name] = python_type
        return super().__new__(cls, name, bases, dct)


class FormComponent(Component, metaclass=FormComponentMetaClass):
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
    form_class: type(forms.BaseForm) = None
    form_submitted: bool = False
    form_errors: dict = {}  # TODO: make protected + include in render context
    _form: Form = None
    _validate_called: bool = False

    # _form_temp_files is an internal storage for temporary uploaded files' handles.
    # it is saved with the state, so it can survive page requests. FIXME! not true!
    _form_temp_files: dict[str, TetraTemporaryUploadedFile] = {}
    _excluded_props_from_saved_state = Component._excluded_props_from_saved_state + [
        "_form_temp_files",
        "_form",
        "_validate_called",
        "form_errors",
    ]

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
        else:
            self._form = self.get_form()

    def get_context_data(self, **kwargs) -> RequestContext:
        if "form" not in kwargs:
            kwargs["form"] = self._form
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = {
            # "initial": self.get_initial(),  # TODO
            # "prefix": self.get_prefix(), # TODO
            "data": self._data(),
            "files": self._form_temp_files,
        }
        return kwargs

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
                form.fields[field_name].widget.attrs.update({"@change": "_uploadFile"})
                if hasattr(field, "temp_file"):
                    # TODO: Check if we need to send back the temp file name and which attribute to use, might not be necessary
                    form.fields[field_name].widget.attrs.update(
                        {"data-tetra-temp-file": field.temp_file}
                    )
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
    def validate(self, field_names: str | list = None) -> dict | None:
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

        # we should not render form errors
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
    def _upload_temp_file(
        self, form_field: str, original_name, file: TetraTemporaryUploadedFile
    ) -> None:
        """Uploads a file to the server temporarily."""
        if not file:
            raise ValueError("File must be provided.")  # TODO: Add validation
        if form_field not in self._form.fields or not isinstance(
            self._form.fields[form_field], FileField
        ):
            raise ValueError(f"Form field '{form_field}' is not a FileField")
        # TODO: further Validate inputs
        # TODO: Add error checking, double check saving file unconditionally

        # keep track of the uploaded file
        self._form_temp_files[form_field] = file
        setattr(self, form_field, file)

    def _reset(self):
        """Internally resets all form fields to their defaults set in load(). This
        internal method is not exposed as a
        public API and can be called by load() too. For client side calls use reset() instead.
        """

        # first, clear all temporary files saved in the component
        try:
            for file_name, file in self._form_temp_files.items():
                self._form_temp_files.pop(file_name)
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
        for field_name, field in self.form_class.base_fields.items():
            setattr(self, field_name, field.initial)
            if self.client and isinstance(field, FileField):
                # we additionally have to set the initial value of FileFields to an empty string
                # as the browser doesn't set the input field
                self.client._setValueByName(field_name, "")

    @public
    def reset(self):
        """Convenience method to be called by the frontend to reset the form.

        All values will be reset to the initial object values.
        """
        self._reset()


class ModelFormComponentMetaClass(FormComponentMetaClass):
    def __new__(cls, name, bases, dct):
        """additionally to FormComponentMetaClass.__new__(), add the object's pk to
        the component's attributes"""
        dct.setdefault("__annotations__", {})
        if "__abstract__" not in dct:
            model = dct.get("model", None)
            abstract = dct.get("__abstract__", False)
            # if no form_class nor model/fields is defined in the new class -> Error
            if (
                not dct.get("form_class", None)
                and (not model or not dct.get("fields", None))
                and not abstract
            ):
                raise AttributeError(
                    f"{name} class requires either a 'form_class' or 'model' and "
                    "'fields' attributes"
                )

            # if form_class is not provided, but model/fields, create a form_class on
            # the fly.
            if "form_class" in dct:
                form_class = dct["form_class"]
                if not issubclass(form_class, forms.ModelForm):
                    raise TypeError(
                        f"'{name}.form_class' must be a "
                        f"subclass of 'ModelForm', not '{form_class.__name__}'"
                    )
                # form_class' model must match the model's class
                elif model and model != form_class.Meta.model:
                    raise TypeError(
                        f"'{name}.form_class.model' must match "
                        f"'{name}.model' class, if provided. "
                        f"({form_class.Meta.model.__name__} != {model.__name__})"
                    )
            else:
                # logger.debug(
                #     f"Creating component attributes from model/fields for class {name}"
                # )
                form_class = modelform_factory(model=dct["model"], fields=dct["fields"])
                dct["form_class"] = form_class

            # So the new class *in any case* has a form_class
        return super().__new__(cls, name, bases, dct)


class ModelFormComponent(FormComponent, metaclass=ModelFormComponentMetaClass):
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
    form_class: type(forms.ModelForm) = None
    model: ModelBase = None
    object: models.Model = None
    fields: list[str] = None
    _context_object_name = None  # TODO
    _excluded_props_from_saved_state = (
        FormComponent._excluded_props_from_saved_state
        + ["_context_object_name", "model", "fields"]
    )

    # def __init__(self, *args, **kwargs):
    #     if not self.model:
    #         self.model = self.get_form_class().Meta.model
    #     super().__init__(*args, **kwargs)

    def get_model(self):
        """Returns the model to use in this component."""
        if not self.model:
            self.model = self.get_form_class()._meta.model
        return self.model

    def get_form_class(self) -> type(forms.ModelForm):
        """Returns the form class to use in this component."""

        # if there is an explicit form_class defined, use it
        if self.form_class:
            return self.form_class
        else:
            raise ImproperlyConfigured(
                f"'{self.__class__.__name__}' must either define 'form_class' "
                "or both 'model' and 'fields', or override 'get_form_class()'"
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
    and calls them to get the current `queryset`, `hidden`, `disabled` and `required`
    status for the corresponding field.
    Use this class as a mixin for a FormComponent and define methods in it according
    to a specific scheme, and create public method that is called when trigger fields
    are changed.

    Usage:
        Create a method that is called whenever a parent field changes its value, using
        the `@public.watch("field_name")` decorator. The method itself could be
        empty. It is just needed as trigger to rerender the form.

        ```python


        @þublic.watch("make")
        def make_changed_dummy(self, value, old_value, attr) -> None:
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

        All these methods are instance methods (with a `self` parameter)
        and should return a boolean value.

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

        return form


# this is just experimental
class WizardFormComponent(FormComponent):
    __abstract__ = True
