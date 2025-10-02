import datetime
import inspect
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from dateutil import parser as datetime_parser
from django.conf import settings
from django.contrib.messages.storage.base import Message
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import UploadedFile
from django.core.files.uploadhandler import FileUploadHandler
from django.db import models
from django.db.models.fields.files import FieldFile
from django.template.loader import render_to_string
from django.utils.text import re_camel_case
from django.utils.timezone import is_aware

from tetra.globals import has_reactive_components
from tetra.types import ComponentData

try:
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
except ImportError:
    channel_layer = None


# list of hardcoded modules that are not searched for components
# this is necessary as some 3rd party modules contain a "components" package with
# other forms of their components. Even tetra.components is meant to be not a
# "components" directory.
# FIXME: This is badly designed, and should be replaced with a non-hardcoded approach
#  someday[tm]
unsupported_modules = ["tetra", "wagtail.documents", "wagtail.images"]

logger = logging.getLogger(__name__)


def camel_case_to_underscore(value: str):
    """
    Splits camelCase and PascalCase and converts to lower case with underscores.
    """
    return re_camel_case.sub(r"_\1", value).strip("_").lower()


def underscore_to_pascal_case(value: str):
    """builds a PascalCase string from a snake_case like."""
    # special case: value is already pascal or camel case, then don't touch it.
    if "_" not in value and not value.islower():
        return value
    return "".join(word.capitalize() for word in value.split("_"))


def render_styles(request):
    libs = list(set(component._library for component in request.tetra_components_used))
    return render_to_string("lib_styles.html", {"libs": libs})


def render_scripts(request, csrf_token):
    libs = list(set(component._library for component in request.tetra_components_used))
    return render_to_string(
        "lib_scripts.html",
        {
            "libs": libs,
            "include_alpine": request.tetra_scripts_placeholder_include_alpine,
            "csrf_token": csrf_token,
            "debug": settings.DEBUG,
            "use_websockets": str(has_reactive_components()).lower()
            and request.META.get("REMOTE_ADDR") in settings.INTERNAL_IPS,
        },
    )


class TetraTemporaryUploadedFile(UploadedFile):
    """
    A file uploaded to a "persistent" temporary location, to be persisted
    across page refreshes.

    Attributes:
        name: The name of the file.
        size: The size of the file in bytes.
        content_type: The content type of the file.
        temp_name: The path to the temporary file. If given, that file is reused.
    """

    # Django's original InMemoryUploadedFile does not support temporary file paths,
    # and TemporaryUploadedFile uses a really temporary file that is deleted when
    # the request is gc'ed. So we need a file that stays where it is until it is
    # deleted manually or saved to its destination.

    def __init__(
        self,
        name: str,
        content_type: str,
        size: int,
        charset,
        content_type_extra=None,
        temp_name=None,
    ):
        _, ext = os.path.splitext(name)
        temp_file = None
        if temp_name:
            try:
                temp_file = open(
                    os.path.join(
                        settings.MEDIA_ROOT,
                        settings.TETRA_TEMP_UPLOAD_PATH,
                        temp_name,
                    ),
                    "rb",
                )
            except FileNotFoundError as e:
                # if the file does not exist, we just use a new temporary file
                logger.warning(e)

        if not temp_file:
            # create a temporary file that is NOT deleted after closing.
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".upload" + ext,
                dir=Path(settings.MEDIA_ROOT) / settings.TETRA_TEMP_UPLOAD_PATH,
                delete=False,
            )

        super().__init__(
            file=temp_file,
            name=name,
            content_type=content_type,
            size=size,
            charset=charset,
            content_type_extra=content_type_extra,
        )

    def temporary_file_path(self):
        """Return the full path of this file."""
        return self.file.name

    def close(self):
        try:
            return self.file.close()
        except FileNotFoundError:
            pass


class PersistentTemporaryFileUploadHandler(FileUploadHandler):
    """
    Upload handler that streams data into a "persistent" (across page requests)
    temporary file, which can be
    saved to its destination when a form is submitted finally.

    Modified after Django's TemporaryFileUploadHandler, but uses a
    TetraTemporaryUploadedFile instead of TemporaryUploadedFile
    """

    def __init__(self, request=None):
        super().__init__(request)
        self.file = None

    def new_file(self, *args, **kwargs):
        """
        Create the file object to append to as data is coming in.
        """
        super().new_file(*args, **kwargs)
        self.file = TetraTemporaryUploadedFile(
            self.file_name, self.content_type, 0, self.charset, self.content_type_extra
        )

    def receive_data_chunk(self, raw_data, start):
        self.file.write(raw_data)

    def file_complete(self, file_size: int) -> TetraTemporaryUploadedFile:
        self.file.seek(0)
        self.file.size = file_size
        return self.file

    def upload_interrupted(self):
        if hasattr(self, "file"):
            temp_location = self.file.temporary_file_path()
            try:
                self.file.close()
                os.remove(temp_location)
            except FileNotFoundError:
                pass


class TetraJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/times and sets.
    Based on DjangoJSONEncoder.

    Encodes all kind of objects into JSON which will then be used in the client side
    Javascript code. It is NOT used for the encrypted state.
    """

    def default(self, obj: Any) -> str | dict | int | list | None:
        # See "Date Time String Format" in the ECMA-262 specification.
        # https://262.ecma-international.org/#sec-date-time-string-format
        if isinstance(obj, datetime.datetime):
            r = obj.isoformat()
            if obj.microsecond:
                # cut last 3 digits from microseconds
                r = r[:23] + r[26:]
            if r.endswith("+00:00"):
                r = r[:-6] + "Z"
            return {"__type": "datetime", "value": r}
        elif isinstance(obj, datetime.date):
            return {"__type": "datetime", "value": obj.isoformat()}
        elif isinstance(obj, datetime.time):
            if is_aware(obj):
                # TODO: investigate this further
                raise ValueError("JSON can't represent timezone-aware times.")
            r = obj.isoformat()
            if obj.microsecond:
                r = r[:12]
            return {"__type": "datetime", "value": r}
        elif isinstance(obj, set):
            return {"__type": "set", "value": list(obj)}
        # TODO: merge from DjangoJSONEncoder:
        # elif isinstance(obj, datetime.timedelta):
        #     return duration_iso_string(obj)
        # elif isinstance(obj, (decimal.Decimal, uuid.UUID, Promise)):
        #     return str(obj)
        elif isinstance(obj, models.Model):
            # just return the object's pk, as it mostly will be used for lookups
            return obj.pk
        # # FIXME: to_json does not work properly
        # elif hasattr(obj, "to_json"):
        #     return {"__type": "generic", "value": obj.to_json()}
        elif isinstance(obj, (FieldFile, TetraTemporaryUploadedFile)):
            # this case rases various errors, so a good options should
            # be to use a try/except for each property and check if there
            # is a file associated with the object

            # Check if there is a file associated with the object
            if not obj:
                return None

            # This is just for initial page loads, where FileFields are initialized with
            # empty FieldFile objects.
            # name can be '' resulting in an error
            if obj.name is None or obj.name == "":
                return None
            # if a file is attached, it must have been uploaded using a component
            # method. In this case, it certainly is a TetraTemporaryUploadedFile

            return {
                "__type": "file",
                "name": obj.name,
                "size": obj.size,
                "content_type": (
                    obj.content_type if hasattr(obj, "content_type") else None
                ),
                "temp_path": (
                    obj.temporary_file_path()
                    if hasattr(obj, "temporary_file_path")
                    and callable(obj.temporary_file_path)
                    else None
                ),
            }
        elif isinstance(obj, Message):
            try:
                # there has to be an uid - else TetraMiddleware is missing
                uid = obj.uid
            except AttributeError:
                raise ImproperlyConfigured(
                    "Message contains no `uid` "
                    "attribute. Make sure you have "
                    "TetraMiddleware installed in your "
                    "settings.MIDDLEWARE"
                )
            return {
                "__type": "message",
                "message": obj.message,
                "level": obj.level,
                "level_tag": obj.level_tag,
                "tags": obj.tags,
                "extra_tags": obj.extra_tags,
                "uid": uid,
                "dismissible": "dismissible" in obj.extra_tags.split(" "),
            }
        else:
            # as last resort, try to serialize into str
            # this is a way of supporting unknown types (like PhoneNumber,
            # etc.) which doesn't make sense to hardcode all here.
            # But if a str can be created from it, we can send it at least to the
            # client, and hope that when we retrieve the data again and transform it
            # back to a field, the field can handle a str.
            # This is a bit hacky for unknown types.
            # If you have problems with this, please let me know.
            try:
                return str(obj)
            except (TypeError, ValueError):
                pass

        return super().default(obj)


class TetraJSONDecoder(json.JSONDecoder):
    """Decoder that decodes JSON from client side Javascript code into Python objects.

    This is NOT used for the encrypted state, just for the JSON data."""

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj) -> Any:
        if "__type" not in obj:
            return obj
        _type: str = obj["__type"]
        if _type == "datetime":
            return datetime_parser.parse(obj["value"])
        elif _type == "set":
            return set(obj["value"])
        elif _type == "file":
            return TetraTemporaryUploadedFile(
                name=obj["name"],
                size=obj["size"],
                content_type=obj["content_type"],
                temp_name=obj["temp_path"],
                charset=settings.DEFAULT_CHARSET,
            )
        elif _type == "message":
            message = Message(
                message=obj["message"],
                level=obj["level"],
                extra_tags=obj["extra_tags"],
            )
            message.uid = obj["uid"] if "uid" in obj else None
            return message
        raise json.JSONDecodeError(f"Cannot decode '{_type}' object from JSON.", obj, 0)


def to_json(obj: Any) -> str:
    return json.dumps(obj, cls=TetraJSONEncoder)


def from_json(s: str) -> ComponentData:
    return json.loads(s, cls=TetraJSONDecoder)


def isclassmethod(method) -> bool:
    bound_to = getattr(method, "__self__", None)
    if not isinstance(bound_to, type):
        # must be bound to a class
        return False
    name = method.__name__
    for cls in bound_to.__mro__:
        descriptor = vars(cls).get(name)
        if descriptor is not None:
            return isinstance(descriptor, classmethod)
    return False


def is_abstract(component) -> bool:
    """Returns True if a component is abstract, False otherwise."""
    return "__abstract__" in component.__dict__ and getattr(
        component, "__abstract__", False
    )


def param_names_exist(method, *args):
    """Checks if the given parameters of the method exist.

    Example:
        param_name_exist(my_method, "name", "age")
    """
    params = list(inspect.signature(method).parameters.keys())
    if params:
        params = params[1:]  # remove "self"
    for arg in args:
        if arg not in params or args.index(arg) != list(params).index(arg):
            return False
    return True


def param_count(method) -> int:
    """Returns the number of parameters, exclusive 'self'."""
    params = list(inspect.signature(method).parameters.keys())
    if params:
        params = params[1:]  # remove "self"
        return len(params)
    else:
        return 0


def remove_surrounding_quotes(string: str) -> str:
    """Removes surrounding single/double quotes from a string."""
    while len(string) > 2 and string[0] == string[-1] and string[0] in ('"', "'"):
        string = string[1:-1]
    return string


class TetraWsResponse:
    """Standard message format for Tetra WebSocket communication"""

    @staticmethod
    def subscription(
        group: str,
        component_id: str,
        status: str = "subscribed",
        message: str | None = None,
    ) -> dict[str, Any]:
        return {
            "type": "subscription",
            "group": group,
            "component_id": component_id,
            "status": status,  # "subscribed", "unsubscribed", "error"
            "message": message or "",
        }

    @staticmethod
    def message(
        group: str, event_name: str, data: Any, sender_id: str | None = None
    ) -> dict[str, Any]:
        return {
            "type": "channel_message",
            "groups": group,
            "data": data,
            "sender_id": sender_id,
            "event_name": event_name,
            # "timestamp": datetime.now(),
        }

    @staticmethod
    def component_update(group: str, topic: str | None = None) -> dict[str, Any]:
        return {"type": "component.update", "group": group, "topic": topic or group}

    @staticmethod
    def component_update_data(group: str, data: dict) -> dict[str, Any]:
        return {
            group: {
                "type": "component.update_data",
                "group": group,
                "data": data,
            },
        }

    @staticmethod
    def component_remove(component_id: str) -> dict[str, Any]:
        return {
            "type": "component.remove",
            "component_id": component_id,
        }

    @staticmethod
    def broadcast(
        message: str, level: str = "info", data: dict | None = None
    ) -> dict[str, Any]:
        return {
            "type": "message.broadcast",
            "level": level,  # "info", "warning", "error", "success"
            "message": message,
            "data": data,
            # "timestamp": datetime.now(),
        }

    @staticmethod
    def error(
        message: str, code: str | None = None, details: dict | None = None
    ) -> dict[str, Any]:
        return {
            "type": "message.error",
            "message": message,
            "code": code or "",
            "details": details or {},
        }
