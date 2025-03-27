import json
import datetime
import os
import tempfile
import logging
from typing import Any

from dateutil import parser as datetime_parser

from django.contrib.messages.storage.base import Message
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import UploadedFile
from django.core.files.uploadhandler import FileUploadHandler
from django.db import models
from django.utils.text import re_camel_case
from django.template.loader import render_to_string
from django.utils.timezone import is_aware
from django.conf import settings

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
            "debug": settings.DEBUG
            and request.META.get("REMOTE_ADDR") in settings.INTERNAL_IPS,
        },
    )


class TetraTemporaryUploadedFile(UploadedFile):
    """
    A file uploaded to a "persistent" temporary location, to be persisted
    across page refreshes.
    """

    # Django's original InMemoryUploadedFile does not support temporary file paths,
    # and TemporaryUploadedFile uses a really temporary file path that is deleted when
    # the page is closed. So we need a file that stays where it is until it is
    # deleted manually or saved to its destination.

    def __init__(
        self,
        name: str,
        content_type: str,
        size: int,
        charset,
        temp_name=None,
        content_type_extra=None,
    ):
        _, ext = os.path.splitext(name)
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
                temp_name = None

        if not temp_name:
            # create a temporary file that is NOT deleted after closing.
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".upload" + ext,
                dir=os.path.join(settings.MEDIA_ROOT, settings.TETRA_TEMP_UPLOAD_PATH),
                delete_on_close=False,
            )
        super().__init__(
            temp_file, name, content_type, size, charset, content_type_extra
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

    Modified after Django's TemporaryFileUploadHandler
    """

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

    def file_complete(self, file_size):
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
    Javascript code.
    """

    def default(self, obj: Any) -> str | dict | int | list:
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
        elif isinstance(obj, TetraTemporaryUploadedFile):
            return obj.name
        elif isinstance(obj, Message):
            try:
                # there has to be an uid - else TetraMiddleware is missing
                uid = obj.uid
            except AttributeError:
                raise ImproperlyConfigured(
                    "Message contains no (money patched) `uid` "
                    "attribute. Make sure you have "
                    "TetraMiddleware installed in yoru "
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
            try:
                return str(obj)
            except (TypeError, ValueError):
                pass

        return super().default(obj)


class TetraJSONDecoder(json.JSONDecoder):
    """Decoder that decodes JSON from client side Javascript code into Python
    objects."""

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
                name=obj["value"]["name"],
                size=obj["value"]["size"],
                content_type=obj["value"]["content_type"],
                temp_name=obj["value"]["temp_path"],
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


def from_json(s: str) -> dict:
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
