import json
import datetime
from dateutil import parser as datetime_parser
from django.utils.text import re_camel_case
from django.template.loader import render_to_string
from django.core.serializers.json import DjangoJSONEncoder
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
        else:
            return super().default(obj)


class TetraJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if "__type" not in obj:
            return obj
        type = obj["__type"]
        if type == "datetime":
            return datetime_parser.parse(obj["value"])
        if type == "set":
            return set(obj["value"])
        return obj


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
