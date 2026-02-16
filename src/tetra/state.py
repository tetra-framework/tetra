import gzip
import base64
import logging
import pickle
import time
import hmac
import hashlib
from copy import copy
from typing import Any, TYPE_CHECKING
from io import BytesIO

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.db.models.query import QuerySet
from django.db.models import Model
from django.db.models.fields.files import FieldFile
from django.http import HttpRequest
from django.template import RequestContext, engines
from django.template.base import Origin
from django.template.loader_tags import BlockNode
from django.utils.functional import SimpleLazyObject, LazyObject
from functools import lru_cache

from .exceptions import ComponentError
from .utils import isclassmethod, NamedTemporaryUploadedFile
from .templates import InlineOrigin

if TYPE_CHECKING:
    from tetra.components import BasicComponent, Component


# Global flags to avoid circular imports
loading_libraries = False
find_libraries_done = False

# State protocol version for security migrations
STATE_VERSION = 1

# Default state token expiration time in seconds (24 hours)
# Can be overridden via TETRA_STATE_MAX_AGE in Django settings
DEFAULT_STATE_MAX_AGE = 24 * 60 * 60


def get_state_max_age() -> int:
    """Get the state token max age from Django settings (lazy evaluation)."""
    from django.conf import settings

    return getattr(settings, "TETRA_STATE_MAX_AGE", DEFAULT_STATE_MAX_AGE)


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


@register_pickler(FieldFile, b"FieldFile")
class PickleFieldFile(Pickler):
    @staticmethod
    def pickle(obj: FieldFile) -> bytes | None:
        return pickle.dumps(
            {
                "model": type(obj.instance),
                "pk": obj.instance.pk,
                "field_name": obj.field.name,
                "name": obj.name,
            }
        )

    @staticmethod
    def unpickle(bs: bytes) -> FieldFile | None:
        data = pickle.loads(bs)
        model = data["model"]
        try:
            instance = model.objects.get(pk=data["pk"])
        except (model.DoesNotExist, AttributeError):
            return None

        field_name = data["field_name"]
        field_file = getattr(instance, field_name)
        if data["name"]:
            field_file.name = data["name"]
        return field_file


@register_pickler(NamedTemporaryUploadedFile, b"NamedTemporaryUploadedFile")
class PickleNamedTemporaryUploadedFile(Pickler):
    @staticmethod
    def pickle(file: NamedTemporaryUploadedFile) -> bytes | None:
        # return a reference to file's temporary location
        return pickle.dumps(
            {
                "name": file.name,
                "size": file.size,
                "content_type": file.content_type,
                "temp_path": file.temporary_file_path(),
            }
        )

    @staticmethod
    def unpickle(bs: bytes) -> NamedTemporaryUploadedFile:
        data = pickle.loads(bs)
        return NamedTemporaryUploadedFile(
            name=data["name"],
            size=data["size"],
            content_type=data["content_type"],
            charset=settings.DEFAULT_CHARSET,
            temp_path=data["temp_path"],
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
    """Custom pickler for serializing component state with support for special object types.

    Extends pickle.Pickler to handle Django-specific objects and custom types that require
    special serialization logic. Uses registered picklers to serialize objects that cannot
    be pickled using standard pickle mechanisms.
    """

    def persistent_id(self, obj) -> bytes | None:
        """Generate a persistent ID for objects requiring custom serialization.

        This method is called by the pickle module for each object during serialization.
        It determines whether an object needs custom handling and returns a persistent ID
        that can be used to reconstruct the object during unpickling.

        The method performs the following steps:
        1. Skips basic types that can be pickled normally
        2. Handles Django Origin objects by removing unpickleable loader references
        3. Resolves lazy objects before pickling
        4. Finds and applies appropriate custom picklers for registered types

        Args:
            obj: The object to be pickled. Can be any Python object.

        Returns:
            bytes | None: A persistent ID in the format b"prefix:pickled_data" if a custom
                pickler is found and successfully serializes the object, None otherwise.
                When None is returned, the standard pickle mechanism is used.
        """
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

        return None


class StateUnpickler(pickle.Unpickler):
    """
    Secure unpickler that only allows known safe types to be unpickled.

    This prevents arbitrary code execution via malicious pickle payloads,
    even if an attacker manages to forge an encrypted state token.
    """

    # Whitelist of safe builtin types that can be unpickled
    SAFE_BUILTINS = {
        "builtins": {
            "list",
            "dict",
            "set",
            "frozenset",
            "tuple",
            "str",
            "int",
            "float",
            "bool",
            "bytes",
            "bytearray",
            "complex",
            "range",
            "type",
            "NoneType",
            "Ellipsis",
            "NotImplementedType",
            "slice",
            "object",
        },
    }

    # Whitelist of safe module.class combinations
    SAFE_MODULES = {
        "datetime": {"datetime", "date", "time", "timedelta", "timezone"},
        "decimal": {"Decimal"},
        "collections": {"OrderedDict", "defaultdict", "Counter", "deque"},
        "pathlib": {"PurePath", "PosixPath", "WindowsPath"},
        "uuid": {"UUID"},
        "django.utils.safestring": {"SafeString", "SafeData", "SafeText"},
    }

    def find_class(self, module: str, name: str) -> type:
        """Override find_class to only allow whitelisted types."""

        # Check if this is a registered custom pickler (highest priority)
        # Custom picklers handle Model, QuerySet, etc. with prefix-based identification
        if name in picklers_by_prefix:
            return picklers_by_prefix[name]

        # Check builtins whitelist
        if module == "builtins" or module == "__builtin__":
            if name in self.SAFE_BUILTINS.get("builtins", set()):
                return getattr(__builtins__, name, None) or getattr(
                    __import__("builtins"), name
                )
            raise StateException(f"Unpickling blocked: unsafe builtin '{name}'")

        # Check module whitelist
        if module in self.SAFE_MODULES:
            if name in self.SAFE_MODULES[module]:
                mod = __import__(module, fromlist=[name])
                return getattr(mod, name)
            raise StateException(
                f"Unpickling blocked: '{module}.{name}' not in safe list"
            )

        # Allow types module for basic types
        if module == "types":
            safe_types = {"NoneType", "FunctionType", "MethodType", "CodeType"}
            if name in safe_types:
                mod = __import__("types")
                return getattr(mod, name)
            raise StateException(f"Unpickling blocked: unsafe type '{name}'")

        # Allow Tetra component classes - they must be BasicComponent subclasses
        try:
            mod = __import__(module, fromlist=[name])
            cls = getattr(mod, name)
            # Verify it's a component class
            from .components import BasicComponent

            if isinstance(cls, type) and issubclass(cls, BasicComponent):
                return cls
        except (ImportError, AttributeError):
            pass

        # Allow Django models (they are handled by custom picklers, but also allow
        # direct class references for component attributes that reference models)
        if module.endswith(".models") or ".models." in module:
            try:
                mod = __import__(module, fromlist=[name])
                cls = getattr(mod, name)
                if isinstance(cls, type) and issubclass(cls, Model):
                    return cls
            except (ImportError, AttributeError):
                pass

        # Allow Django forms
        if module == "django.forms" or module.startswith("django.forms."):
            try:
                mod = __import__(module, fromlist=[name])
                return getattr(mod, name)
            except (ImportError, AttributeError):
                pass

        # Block everything else
        raise StateException(
            f"Unpickling blocked: '{module}.{name}' is not in the allowed list. "
            f"If you need to serialize this type, register a custom pickler."
        )

    def persistent_load(self, persistent_id: bytes | None) -> Any | None:
        """Handle custom persistent IDs from registered picklers."""
        if not persistent_id:
            return None
        try:
            prefix, data = persistent_id.split(b":", 1)
            if prefix in picklers_by_prefix:
                pickler = picklers_by_prefix[prefix]
                return pickler.unpickle(data)
        except Exception as e:
            raise StateException(f"Failed to unpickle custom type: {e}")
        raise StateException(
            f"Unknown persistent ID prefix: {prefix!r}. "
            "This could indicate a corrupted or tampered state token."
        )


@lru_cache(maxsize=1)
def _get_state_signature_key() -> bytes:
    """Generate a cryptographic key used to verify the integrity of Tetra component
    state signatures."""
    """Get a separate key for state signature verification."""
    key_material = settings.SECRET_KEY.encode() + b"tetra-state-signature"
    return hashlib.sha256(key_material).digest()


def _sign_state(data: bytes, timestamp: int, version: int) -> str:
    """Create an HMAC signature for the state data."""
    key = _get_state_signature_key()
    message = f"{version}:{timestamp}:".encode() + data
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _verify_signature(
    data: bytes, timestamp: int, version: int, signature: str
) -> bool:
    """Verify the HMAC signature of state data."""
    expected = _sign_state(data, timestamp, version)
    return hmac.compare_digest(expected, signature)


def pickle_state(obj) -> bytes:
    out = BytesIO()
    try:
        StatePickler(out).dump(obj)
    except pickle.PicklingError as e:
        raise ComponentError(f"Failed to pickle state for {obj}: {e}")
    return out.getvalue()


def unpickle_state(data) -> Any | None:
    return StateUnpickler(BytesIO(data)).load()


def _get_fernet_for_request(request: HttpRequest) -> Fernet:
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


def encode_component(component: "BasicComponent") -> str:
    """
    Serializes a component with its server state into an encrypted state token.

    The token includes:
    - State version for future security migrations
    - Timestamp for expiration checks
    - HMAC signature for integrity verification
    - Gzip compression for efficiency
    - Fernet encryption for confidentiality
    """
    fernet = _get_fernet_for_request(component.request)

    # TODO: this should be in component.__getstate__
    # We don't need a full context stack and don't want a RequestContext
    # TODO: in future would be better to patch RequestContext to keep track of what
    #  it adds that then they can be easily removed.
    original_context = component._context
    context = copy(original_context) or {}
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

    pickled_state = pickle_state(component)
    component._context = original_context

    # Compress the pickled state
    compressed_state = gzip.compress(pickled_state)

    # Add timestamp and version for security
    timestamp = int(time.time())

    # Create signature for integrity verification
    signature = _sign_state(compressed_state, timestamp, STATE_VERSION)

    # Build the state envelope: version:timestamp:signature:compressed_data
    envelope = f"{STATE_VERSION}:{timestamp}:{signature}:".encode() + compressed_state

    # Encrypt the entire envelope
    state_token = fernet.encrypt(envelope).decode()
    return state_token


def decode_component(state_token: str, request: HttpRequest) -> "Component":
    """
    Deserializes a pickled state token into a component, resuming its state.

    This function:
    1. Decrypts the token using the session-specific Fernet key
    2. Verifies the state version
    3. Checks the timestamp for expiration
    4. Verifies the HMAC signature for integrity
    5. Decompresses and unpickles the state

    Raises:
        StateException: If the token is expired, corrupted, or has invalid signature
        ComponentError: If the state cannot be unpickled
    """
    fernet = _get_fernet_for_request(request)

    try:
        # Decrypt the token
        envelope = fernet.decrypt(state_token.encode())
    except Exception as e:
        raise StateException(f"Failed to decrypt state token: {e}")

    # Parse the envelope: version:timestamp:signature:compressed_data
    try:
        # Find the colons that separate header fields
        first_colon = envelope.find(b":")
        second_colon = envelope.find(b":", first_colon + 1)
        third_colon = envelope.find(b":", second_colon + 1)

        if first_colon == -1 or second_colon == -1 or third_colon == -1:
            raise StateException("Invalid state token format")

        version = int(envelope[:first_colon].decode())
        timestamp = int(envelope[first_colon + 1 : second_colon].decode())
        signature = envelope[second_colon + 1 : third_colon].decode()
        compressed_state = envelope[third_colon + 1 :]

    except (ValueError, UnicodeDecodeError) as e:
        raise StateException(f"Failed to parse state token header: {e}")

    # Check version compatibility
    if version != STATE_VERSION:
        raise StateException(
            f"State version mismatch: expected {STATE_VERSION}, got {version}. "
            "The page may need to be refreshed."
        )

    # Check expiration
    current_time = int(time.time())
    age = current_time - timestamp
    max_age = get_state_max_age()
    if age > max_age:
        raise StateException(
            f"State token expired (age: {age}s, max: {max_age}s). "
            "Please refresh the page."
        )

    # Verify signature
    if not _verify_signature(compressed_state, timestamp, version, signature):
        raise StateException(
            "State token signature verification failed. "
            "The token may have been tampered with."
        )

    # Decompress and unpickle
    try:
        pickled_state = gzip.decompress(compressed_state)
        component: Component = unpickle_state(pickled_state)
    except Exception as e:
        raise StateException(f"Failed to decode state: {e}")

    return component
