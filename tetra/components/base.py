from copy import copy
from typing import Optional
from types import FunctionType
from enum import Enum
import inspect
import re
import itertools
from weakref import WeakKeyDictionary
from functools import wraps
from threading import local

from django.template.loader import render_to_string
from django.template import RequestContext, TemplateSyntaxError
from django.template.loader_tags import BLOCK_CONTEXT_KEY, BlockContext, BlockNode
from django.utils.safestring import mark_safe
from django.utils.html import escapejs, escape
from django.utils.functional import SimpleLazyObject
from django.http import JsonResponse
from django.urls import reverse

from ..utils import camel_case_to_underscore, to_json, TetraJSONEncoder, isclassmethod
from ..state import encode_component, decode_component
from ..templates import InlineOrigin, InlineTemplate

from .callbacks import CallbackList


thread_local = local()


class ComponentException(Exception):
    pass


class ComponentNotFound(ComponentException):
    pass


def make_template(cls):
    from ..templatetags.tetra import get_nodes_by_type_deep

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
        # By default we want to compile templates during python compile time, however
        # the template exceptions are much better when raised at runtime as it shows
        # a nice stack trace in the browser. We therefore create a "Lazy" template
        # after a compile error that will run in the browser when testing.
        # TODO: turn this off when DEBUG=False
        making_lazy_after_exception = True
        template = SimpleLazyObject(
            lambda: InlineTemplate(
                "{% load tetra %}" + cls.template,
                origin=origin,
            )
        )
    if not making_lazy_after_exception:
        for i, block_node in enumerate(
            get_nodes_by_type_deep(template.nodelist, BlockNode)
        ):
            if not getattr(block_node, "origin", None):
                block_node.origin = origin
    return template


class BasicComponentMetaClass(type):
    def __new__(mcls, name, bases, attrs):
        newcls = super().__new__(mcls, name, bases, attrs)
        newcls._name = camel_case_to_underscore(newcls.__name__)
        if hasattr(newcls, "template"):
            newcls._template = make_template(newcls)
        return newcls


class RenderData(Enum):
    INIT = 0
    MAINTAIN = 1
    UPDATE = 2


class BasicComponent(object, metaclass=BasicComponentMetaClass):
    style: Optional[str] = None
    _name = None
    _library = None
    _app = None
    _leaded_from_state = False

    def __init__(
        self, _request, _attrs=None, _context=None, _blocks=None, *args, **kwargs
    ):
        self.request = _request
        self.attrs = _attrs
        self._context = _context
        self._blocks = _blocks
        self._call_load(*args, **kwargs)

    @classmethod
    def full_component_name(cls):
        return f"{cls._library.app.label}__{cls._library.name}__{cls._name}"

    @classmethod
    def get_source_location(cls):
        filename = inspect.getsourcefile(cls)
        lines, start = inspect.getsourcelines(cls)
        return filename, start, len(lines)

    @classmethod
    def get_template_source_location(cls):
        filename, comp_start, com_end = cls.get_source_location()
        if not hasattr(cls, "template") or not cls.template:
            return filename, None
        with open(filename, "r") as f:
            source = f.read()
        start = source.index(cls.template)
        line = source[:start].count("\n") + 1
        return filename, line

    @classmethod
    def has_script(cls):
        return False

    @classmethod
    def has_styles(cls):
        return bool(hasattr(cls, "style") and cls.style)

    @classmethod
    def make_styles(cls):
        return cls.style

    @classmethod
    def make_styles_file(cls):
        filename, comp_start_line, source_len = cls.get_source_location()
        with open(filename, "r") as f:
            py_source = f.read()
        comp_start_offset = len("\n".join(py_source.split("\n")[:comp_start_line]))
        start = py_source.index(cls.style, comp_start_offset)
        before = py_source[:start]
        before = re.sub(f"\S", " ", before)
        return f"{before}{cls.style}"

    @classmethod
    def as_tag(cls, _request, *args, **kwargs):
        if not hasattr(_request, "tetra_components_used"):
            _request.tetra_components_used = set()
        _request.tetra_components_used.add(cls)
        return cls(_request, *args, **kwargs).render()

    def _call_load(self, *args, **kwargs):
        self.load(*args, **kwargs)

    def load(self) -> None:
        pass

    def _add_to_context(self, context):
        for key in dir(self):
            if not (key.startswith("_") or isclassmethod(getattr(self, key))):
                context[key] = getattr(self, key)

    def render(self):
        if isinstance(self._context, RequestContext):
            context = self._context
        else:
            context = RequestContext(self.request, self._context)
        self._add_to_context(context)

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


empty = object()


class PublicMeta(type):
    def __getattr__(self, name):
        if hasattr(self, f"do_{name}"):
            inst = self()
            return getattr(inst, f"do_{name}")
        else:
            raise AttributeError(f"Public decorator has no method {name}.")


class Public(metaclass=PublicMeta):
    def __init__(self, obj=None, update=True):
        self._update = update
        self._watch = []
        self._debounce = None
        self._debounce_immediate = None
        self._throttle = None
        self._throttle_trailing = None
        self._throttle_leading = None
        self.__call__(obj)

    def __call__(self, obj):
        if self._update and isinstance(obj, FunctionType):

            @wraps(obj)
            def fn(self, *args, **kwards):
                ret = obj(self, *args, **kwards)
                self.update()
                return ret

            self.obj = fn
        else:
            self.obj = obj
        return self

    def __getattr__(self, name):
        if hasattr(self, f"do_{name}"):
            return getattr(self, f"do_{name}")
        else:
            raise AttributeError(f"Public decorator has no method {name}.")

    def do_watch(self, *args):
        for arg in args:
            if isinstance(arg, str):
                self._watch.append(arg)
            else:
                self._watch.extend(arg)
        return self

    def do_debounce(self, timeout, immediate=False):
        self._debounce = timeout
        self._debounce_immediate = immediate
        return self

    def do_throttle(self, timeout, trailing=False, leading=True):
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

    def __init__(self, _request, key=None, *args, **kwargs):
        super().__init__(_request, *args, **kwargs)
        self.key = key

    @classmethod
    def from_state(
        cls,
        data,
        request,
        key=None,
        _attrs=None,
        _context=None,
        _blocks=None,
        *args,
        **kwargs,
    ):
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
            raise TypeError("Component of ivalid type.")

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
        return component

    @classmethod
    def has_script(cls):
        return bool(cls.script)

    @classmethod
    def _component_url(cls, method_name):
        return reverse(
            "tetra_public_component_method",
            args=[cls._library.app.label, cls._library.name, cls._name, method_name],
        )

    @classmethod
    def make_script(cls, component_var=None):
        component_server_methods = []
        for method in cls._public_methods:
            method_data = copy(method)
            method_data["endpoint"] = (cls._component_url(method["name"]),)
            component_server_methods.append(method_data)
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
    def make_script_file(cls):
        filename, comp_start_line, source_len = cls.get_source_location()
        with open(filename, "r") as f:
            py_source = f.read()
        comp_start_offset = len("\n".join(py_source.split("\n")[:comp_start_line]))
        start = py_source.index(cls.script, comp_start_offset)
        before = py_source[:start]
        before = re.sub(f"\S", " ", before)
        return f"{before}{cls.script}"

    def _call_load(self, *args, **kwargs):
        self._load_args = args
        self._load_kwargs = kwargs
        tracing_component_load[self] = set()
        try:
            self.load(*args, **kwargs)
            props = tracing_component_load[self]
        finally:
            del tracing_component_load[self]
        self._excluded_load_props_from_saved_state = list(props)

    def _recall_load(self):
        self._call_load(*self._load_args, **self._load_kwargs)

    def __setattr__(self, item, value):
        if self in tracing_component_load:
            tracing_component_load[self].add(item)
        return super().__setattr__(item, value)

    @property
    def client(self):
        return self._callback_queue

    def set_load_args(self, *args, **kwargs) -> None:
        load_args = {
            "args": args,
            "kwargs": kwargs,
        }
        try:
            to_json(load_args)
        except TypeError:
            raise ComponentException(
                f"Tetra Component {self.__class__.__name__} tried to self.set_load_args() with a none json serializable value."
            )
        self._load_args = load_args

    def _data(self):
        return {key: getattr(self, key) for key in self._public_properties}

    def _encoded_state(self):
        return encode_component(self)

    def __getstate__(self):
        state = self.__dict__.copy()
        for key in (
            self._excluded_props_from_saved_state
            + self._excluded_load_props_from_saved_state
        ):
            if key in state:
                del state[key]
        return state

    def _render_data(self):
        data = self._data()
        data["__state"] = self._encoded_state()
        return data

    def _add_to_context(self, context):
        super()._add_to_context(context)
        if hasattr(self, "_loaded_children_state") and self._loaded_children_state:
            children_state = {c["data"]["key"]: c for c in self._loaded_children_state}
            context["_loaded_children_state"] = children_state
        else:
            context["_loaded_children_state"] = None

    def render(self, data=RenderData.INIT):
        if hasattr(thread_local, "_tetra_render_data"):
            data = thread_local._tetra_render_data
            set_thread_local = False
        else:
            thread_local._tetra_render_data = data
            set_thread_local = True
        html = super().render()
        if set_thread_local:
            del thread_local._tetra_render_data
        tag_name_end = re.match(r"^\s*<\w+", html).end(0)
        extra_tags = [
            f'tetra-component="{self.full_component_name()}"',
            f'x-bind="__rootBind"',
        ]
        if self.key:
            extra_tags.append(f'key="{self.key}"')
        if data == RenderData.UPDATE and self._leaded_from_state:
            data_json = escape(to_json(self._render_data()))
            old_data_json = escape(to_json(self._leaded_from_state_data))
            extra_tags.append(f"x-data=\"\"")
            extra_tags.append(f'x-data-update="{data_json}"')
            extra_tags.append(f'x-data-update-old="{old_data_json}"')
        elif data == RenderData.MAINTAIN:
            extra_tags.append(f"x-data=\"\"")
            extra_tags.append(f"x-data-maintain")
        else:
            data_json = escapejs(to_json(self._render_data()))
            extra_tags.append(f"x-data=\"{self.full_component_name()}('{data_json}')\"")
        html = f'{html[:tag_name_end]} {" ".join(extra_tags)} {html[tag_name_end:]}'
        return mark_safe(html)

    def update_html(self, include_state=False):
        if include_state:
            self.client._updateHtml(self.render(data=RenderData.UPDATE))
        else:
            self.client._updateHtml(self.render(data=RenderData.MAINTAIN))

    def update_data(self):
        self.client._updateData(self._render_data())

    def update(self):
        self.update_html(include_state=True)

    def replace_component(self):
        self.client._replaceComponent(self.render())

    def _call_public_method(self, request, method_name, children_state, *args):
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
    def _refresh(self):
        """
        Re-render and return
        This is just a noop as the @public decorator implements this functionality
        """
        pass

