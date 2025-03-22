import gzip
import base64
import logging
import pickle
from copy import copy
from typing import Any, TYPE_CHECKING
from io import BytesIO

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.db.models.query import QuerySet
from django.db.models import Model
from django.template import RequestContext, engines
from django.template.base import Origin
from django.template.loader_tags import BlockNode
from django.utils.functional import SimpleLazyObject, LazyObject

from .exceptions import ComponentError
from .utils import isclassmethod, TetraTemporaryUploadedFile
from .templates import InlineOrigin

if TYPE_CHECKING:
    from tetra.components import Component


class StateException(Exception):
    pass


logger = logging.getLogger(__name__)
picklers_by_type = {}
picklers_by_prefix = {}


class Pickler:
    """Base class for picklers.

    Define pickle and unpickle methods in a subclass and register it with
    the `register_pickler` decorator, e.g.

    ```python
    @register_pickler(MyObjectPickler, b"MyObject")
    ```
    """

    @staticmethod
    def pickle(obj: Any) -> bytes | None:
        pass

    @staticmethod
    def unpickle(bs: bytes) -> Any:
        pass


def register_pickler(obj_type, prefix: bytes):
    """Decorator for registering classes as picklers.

    See [Pickler](Pickler) class on how to implement a pickler.
    """

    def dec(cls):
        cls.obj_type = obj_type
        cls.prefix = prefix
        picklers_by_type[obj_type] = cls
        picklers_by_prefix[prefix] = cls
        return cls

    return dec


def resolve_lazy_object(lazy_object: Model | LazyObject) -> Model:
    """If it's a SimpleLazyObject, resolve it by accessing the underlying object."""
    if isinstance(lazy_object, SimpleLazyObject):
        return lazy_object._wrapped
    return lazy_object


# ----------- Picklers ------------
# see https://tetra.readthedocs.io/en/stable/state-security/


@register_pickler(QuerySet, b"QuerySet")
class PickleQuerySet(Pickler):
    @staticmethod
    def pickle(qs: QuerySet) -> bytes | None:
        return pickle.dumps(
            {
                "model": qs.model,
                "query": qs.query,
            }
        )

    @staticmethod
    def unpickle(bs: bytes) -> Any:
        data = pickle.loads(bs)
        qs = data["model"].objects.all()
        qs.query = data["query"]
        return qs


@register_pickler(Model, b"Model")
class PickleModel(Pickler):
    @staticmethod
    def pickle(obj: Model) -> bytes | None:
        return pickle.dumps(
            {
                "class": type(obj),
                "pk": obj.pk,
            }
        )

    @staticmethod
    def unpickle(bs: bytes) -> Model | None:
        data = pickle.loads(bs)
        model = data["class"]
        try:
            return model.objects.get(pk=data["pk"])
        except model.DoesNotExist:
            return None


@register_pickler(TetraTemporaryUploadedFile, b"PersistentTemporaryUploadedFile")
class PicklePersistentTemporaryUploadedFile(Pickler):
    @staticmethod
    def pickle(file: TetraTemporaryUploadedFile) -> bytes | None:
        # return a reference to file's temporary location
        value = pickle.dumps(
            {
                "name": file.name,
                "size": file.size,
                "content_type": file.content_type,
                "temp_path": file.temporary_file_path(),
            }
        )
        return value

    @staticmethod
    def unpickle(bs: bytes) -> Any:
        data = pickle.loads(bs)
        return TetraTemporaryUploadedFile(
            name=data["name"],
            size=data["size"],
            content_type=data["content_type"],
            charset=settings.DEFAULT_CHARSET,
            temp_name=data["temp_path"],
        )


@register_pickler(BlockNode, b"BlockNode")
class PickleBlockNode(Pickler):
    def pickle(obj: Origin) -> bytes | None:
        origin = getattr(obj, "origin", None)
        if isinstance(origin, InlineOrigin) and hasattr(obj, "_path_key"):
            return pickle.dumps(
                {
                    "component": origin.component,
                    "block_path_key": obj._path_key,
                }
            )
        elif hasattr(obj, "_path_key"):
            return pickle.dumps(
                {
                    "loader_module": origin.loader.__class__.__module__,
                    "loader_name": origin.loader.__class__.__name__,
                    "template_name": origin.template_name,
                    "block_path_key": obj._path_key,
                }
            )
        return None

    def unpickle(bs: bytes) -> Origin:
        data = pickle.loads(bs)
        if "loader_name" in data:
            loader = engines["django"].engine.find_template_loader(
                f"{data['loader_module']}.{data['loader_name']}"
            )
            template = loader.get_template(data["template_name"])
            block = template.blocks_by_key[data["block_path_key"]]
            return block
        elif "component" in data:
            return data["component"]._template.blocks_by_key[data["block_path_key"]]
        else:
            raise TypeError("Unpicked data for template block incorrect.")


# @register_pickler(Form, b"Form")
# class PickleForm(Pickler):
#     """This is just a stub pickler that always returns empty bytes when ṕickling
#     a form."""
#
#     def pickle(form: Form) -> bytes | None:
#         return b""
#
#     def unpickle(bs: bytes) -> Form | None:
#         return None
#
#
# @register_pickler(widgets.Widget, b"Widget")
# class PickleWidget(Pickler):
#     @staticmethod
#     def pickle(widget: widgets.Widget) -> bytes | None:
#         print("PICKLE WIDGET!")
#         return pickle.dumps(
#             {
#                 "class": widget.__class__.__name__,
#                 "module": widget.__class__.__module__,
#                 "attrs": getattr(widget, "attrs", {}),
#             }
#         )
#
#     @staticmethod
#     def unpickle(bs: bytes) -> Any:
#         data = pickle.loads(bs)
#         module = importlib.import_module(data["module"])
#         widget_class = getattr(module, data["class"])
#         widget = widget_class()
#         widget.attrs = data["attrs"]
#         return widget
#
#
skip_check = {
    str,
    bytes,
    int,
    float,
    bool,
    dict,
    list,
    set,
    frozenset,
    tuple,
    range,
    bytes,
    bytearray,
    complex,
    type(None),
}


class StatePickler(pickle.Pickler):
    def persistent_id(self, obj) -> bytes | None:
        if type(obj) in skip_check:
            return None

        # Template loaders are not pickleable, they are set as the 'loader' property
        # on block.origin which is an Origin obj. We set `obj.loader = None` to
        # stop it from erroring.
        # This will make error messages about templates a little less helpful, however
        # we have already rendered the template once and so it's not likely we will get
        # an exception.
        if isinstance(obj, Origin):
            obj.loader = None

        # for LazyObjects, resolve them before pickling
        obj = resolve_lazy_object(obj)

        pickler = None
        if type(obj) in picklers_by_type:
            pickler = picklers_by_type[type(obj)]
        else:
            for obj_type, pickler_option in picklers_by_type.items():
                if isinstance(obj, obj_type):
                    pickler = pickler_option
        if pickler:
            pickled = pickler.pickle(obj)
            if pickled is not None:
                return b":".join([pickler.prefix, pickled])


class StateUnpickler(pickle.Unpickler):
    def persistent_load(self, persistent_id: bytes | None) -> Any | None:
        prefix, data = persistent_id.split(b":", 1)
        if prefix in picklers_by_prefix:
            pickler = picklers_by_prefix[prefix]
            return pickler.unpickle(data)
        return None


def pickle_state(obj) -> bytes:
    out = BytesIO()
    try:
        StatePickler(out).dump(obj)
    except pickle.PicklingError as e:
        raise ComponentError(f"Failed to pickle state for {obj}: {e}")
    return out.getvalue()


def unpickle_state(data) -> Any | None:
    return StateUnpickler(BytesIO(data)).load()


def _get_fernet_for_request(request):
    if hasattr(request, "_tetra_state_fernet") and request._tetra_state_fernet:
        return request._tetra_state_fernet
    if not request.session.session_key:
        request.session.create()
    salt = "".join(
        [
            request.session.session_key,
            request.user.get_username() if request.user.is_authenticated else "",
        ]
    )
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode(),
        info=b"tetra-state",
    )
    key = base64.urlsafe_b64encode(hkdf.derive(settings.SECRET_KEY.encode()))
    fernet = Fernet(key)
    request._tetra_state_fernet = fernet
    return fernet


# These are the default context vars from BaseContext RequestContext, and few extra
keys_to_remove_from_context = [
    "True",
    "False",
    "None",
    "csrf_token",
    "request",
    "user",
    "perms",
    "messages",
    "DEFAULT_MESSAGE_LEVELS",
    "template",
    "_template",
]


def encode_component(component) -> str:
    fernet = _get_fernet_for_request(component.request)

    # TODO: this should be in component.__getstate__
    # We don't need a full context stack and don't want a RequestContext
    # TODO: in future would be better to patch RequestContext to keep track of what
    #  it adds that then they can be easily removed.
    original_context = component._context
    context = copy(original_context)
    if isinstance(context, RequestContext):
        # Remove the top to layer of the context dicts:
        # 0: is the template defaults (True, False, None etc.)
        # 1: is the context added by RequestContext
        context.dicts = context.dicts[2:]
    if hasattr(context, "flatten"):
        context = context.flatten()
    for key in keys_to_remove_from_context:
        context.pop(key, None)
    for key in dir(component):
        # Remove vars from context that are filled from the component
        if not (
            key.startswith("_")
            or isclassmethod(getattr(component.__class__, key, None))
        ):
            context.pop(key, None)
    component._context = context
    # logger.debug(
    #     f"State before encoding: {component._data()}",
    # )
    pickled_component = pickle_state(component)
    component._context = original_context

    state_token = fernet.encrypt(gzip.compress(pickled_component)).decode()
    return state_token


def decode_component(state_token, request) -> "Component":
    fernet = _get_fernet_for_request(request)
    component: Component = unpickle_state(
        gzip.decompress(fernet.decrypt(state_token.encode()))
    )
    # logger.debug(
    #     f"State after decoding:  {component._data()}",
    # )
    return component
