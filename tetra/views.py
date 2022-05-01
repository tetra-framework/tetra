import json
from django.http import HttpResponseNotFound, HttpResponseBadRequest
from .component_register import libraries
from .state import decode_component
from .utils import from_json


def component_method(request, app_name, library_name, component_name, method_name):
    if not request.method == "POST":
        return HttpResponseBadRequest()

    try:
        Component = libraries[app_name][library_name].components[component_name]
    except KeyError:
        return HttpResponseNotFound()

    if not method_name in (m["name"] for m in Component._public_methods):
        return HttpResponseNotFound()

    try:
        data = from_json(request.body.decode())
    except json.decoder.JSONDecodeError:
        return HttpResponseBadRequest()

    if not (
        isinstance(data, dict) and "args" in data and isinstance(data["args"], list)
    ):
        raise TypeError("Invalid Args value.")

    if not hasattr(request, "tetra_components_used"):
        request.tetra_components_used = set()
    request.tetra_components_used.add(Component)

    component = Component.from_state(data, request)

    return component._call_public_method(
        request, method_name, data["children"], *data["args"]
    )
