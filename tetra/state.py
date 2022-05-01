from copy import copy
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import gzip
import base64
from django.conf import settings
from django.db.models.query import QuerySet
from django.db.models import Model
from django.template import RequestContext, engines
from django.template.base import Origin
from django.template.loader_tags import BlockNode
import pickle
from io import BytesIO
from .utils import isclassmethod
from .templates import InlineOrigin


class StateException(Exception):
    pass


picklers_by_type = {}
picklers_by_prefix = {}


def register_pickler(obj_type, prefix):
    def dec(cls):
        cls.obj_type = obj_type
        cls.prefix = prefix
        picklers_by_type[obj_type] = cls
        picklers_by_prefix[prefix] = cls
        return cls

    return dec


@register_pickler(QuerySet, b"QuerySet")
class PickleQuerySet:
    def pickle(qs):
        return pickle.dumps(
            {
                "model": qs.model,
                "query": qs.query,
            }
        )

    def unpickle(bs):
        data = pickle.loads(bs)
        qs = data["model"].objects.all()
        qs.query = data["query"]
        return qs


@register_pickler(Model, b"Model")
class PickleModel:
    def pickle(obj):
        return pickle.dumps(
            {
                "class": type(obj),
                "pk": obj.pk,
            }
        )

    def unpickle(bs):
        data = pickle.loads(bs)
        model = data["class"]
        try:
            return model.objects.get(pk=data["pk"])
        except model.DoesNotExist:
            return None


@register_pickler(BlockNode, b"BlockNode")
class PickleBlockNode:
    def pickle(obj):
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

    def unpickle(obj):
        data = pickle.loads(obj)
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


skip_check = set(
    [
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
    ]
)


class StatePickler(pickle.Pickler):
    def persistent_id(self, obj):
        if type(obj) in skip_check:
            return None

        # Template loaders are not pickleable, they are set as the 'loader' property
        # on block.obigin which is an Origin obj. We set `obj.loader = None` to
        # stop it from erroring.
        # This will make error messages about templates a little less helpfull, however
        # we have allready rendered the template once and so it's not likely we will get
        # an exception.
        if isinstance(obj, Origin):
            obj.loader = None

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
        return None


class StateUnpickler(pickle.Unpickler):
    def persistent_load(self, persistent_id):
        prefix, data = persistent_id.split(b":", 1)
        if prefix in picklers_by_prefix:
            pickler = picklers_by_prefix[prefix]
            return pickler.unpickle(data)
        return None


def pickle_state(obj):
    out = BytesIO()
    StatePickler(out).dump(obj)
    return out.getvalue()


def unpickle_state(data):
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


def encode_component(component):
    fernet = _get_fernet_for_request(component.request)

    # TODO: this should be in component.__getstate__
    # We don't need a full context stack and don't want a RequestContext
    # TODO: in future would be  better to patch RequestContext to keep track of what
    # it adds that then they can be easily removed.
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
        if not (key.startswith("_") or isclassmethod(getattr(component, key))):
            context.pop(key, None)
    component._context = context

    pickled_component = pickle_state(component)

    component._context = original_context

    state_token = fernet.encrypt(gzip.compress(pickled_component)).decode()
    return state_token


def decode_component(state_token, request):
    fernet = _get_fernet_for_request(request)
    s = gzip.decompress(fernet.decrypt(state_token.encode()))
    state = unpickle_state(gzip.decompress(fernet.decrypt(state_token.encode())))
    return state
