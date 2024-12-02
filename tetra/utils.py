import json
import datetime
from typing import Any

from dateutil import parser as datetime_parser
from django.apps import apps
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


class TetraJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/times and sets.
    Based on DjangoJSONEncoder
    """

    def default(self, obj: Any) -> str | dict | int | list:
        # See "Date Time String Format" in the ECMA-262 specification.
        # https://262.ecma-international.org/#sec-date-time-string-format
        if isinstance(obj, datetime.datetime):
            r = obj.isoformat()
            if obj.microsecond:
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
        else:
            # as last resort, try to serialize into str
            try:
                return str(obj)
            except (TypeError, ValueError):
                pass

        return super().default(obj)


class TetraJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj) -> Any:
        if "__type" not in obj:
            return obj
        _type: str = obj["__type"]
        if _type == "datetime":
            return datetime_parser.parse(obj["value"])
        if _type == "set":
            return set(obj["value"])
        raise json.JSONDecodeError(f"Cannot decode '{_type}' object from JSON.", obj, 0)


def to_json(obj):
    return json.dumps(obj, cls=TetraJSONEncoder)


def from_json(s):
    return json.loads(s, cls=TetraJSONDecoder)


def isclassmethod(method):
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
