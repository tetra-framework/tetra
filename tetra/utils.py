import json
import datetime
from typing import Any

from dateutil import parser as datetime_parser
from django.apps import apps
from django.db import models
from django.utils.text import re_camel_case
from django.template.loader import render_to_string
from django.utils.timezone import is_aware


def camel_case_to_underscore(value):
    """
    Splits CamelCase and converts to lower case with underscores.
    """
    return re_camel_case.sub(r"_\1", value).strip("_").lower()


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
        },
    )


class TetraJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/times and sets.
    Based on DjangoJSONEncoder
    """

    def default(self, obj):
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
            return {
                "__type": f"model.{obj._meta.app_label}.{obj.__class__.__name__}",
                "value": obj.pk,
            }
        else:
            return super().default(obj)


class TetraJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if "__type" not in obj:
            return obj
        _type: str = obj["__type"]
        if _type == "datetime":
            return datetime_parser.parse(obj["value"])
        if _type == "set":
            return set(obj["value"])
        if _type.startswith("model."):
            _, app_name, model_name = _type.split(".")
            model = apps.get_model(app_name, model_name)
            # FIXME: error handling if model.DoesNotExist
            m = model._default_manager.get(pk=obj["value"])
            return m
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
