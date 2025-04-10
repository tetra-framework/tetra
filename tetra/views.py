import json
import logging

from django.http import HttpResponseNotFound, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from tetra.types import ComponentData
from . import Library
from .utils import from_json, PersistentTemporaryFileUploadHandler


logger = logging.getLogger(__name__)


@csrf_exempt
def component_method(request, *args, **kwargs):
    """Override default upload handlers, to create a "persistent" temporary file for
    file uploads that are done using Tetra methods."""
    request.upload_handlers = [PersistentTemporaryFileUploadHandler(request)]
    return _component_method(request, *args, **kwargs)


@csrf_protect
def _component_method(
    request, app_name, library_name, component_name, method_name
) -> HttpResponse:
    if not request.method == "POST":
        return HttpResponseBadRequest()
    try:
        Component = Library.registry[app_name][library_name].components[component_name]
    except KeyError:
        return HttpResponseNotFound()

    if method_name not in (m["name"] for m in Component._public_methods):
        logger.warning(
            f"Tetra method was requested, but not found: {component_name}.{method_name}()"
        )
        return HttpResponseNotFound()

    try:
        # check if request includes multipart/form-data files
        if request.content_type == "multipart/form-data":
            component_state = from_json(request.POST["component_state"])
            # data["args"].extend(request.FILES.values())
        elif request.content_type == "application/json" and request.body:
            # if request is application-data/json, we need to decode it ourselves
            component_state = from_json(request.body.decode())
        else:
            logger.error("Unsupported content type: %s", request.content_type)
            return HttpResponseBadRequest()

    except json.decoder.JSONDecodeError as e:
        logger.error(e)
        return HttpResponseBadRequest()

    if not (
        isinstance(component_state, dict)
        and "args" in component_state
        and isinstance(component_state["args"], list)
    ):
        raise TypeError("Invalid component state args.")

    if not hasattr(request, "tetra_components_used"):
        request.tetra_components_used = set()
    request.tetra_components_used.add(Component)

    component = Component.from_state(component_state, request)

    logger.debug(
        f"Calling component method {component.__class__.__name__}.{method_name}()"
    )
    return component._call_public_method(
        request, method_name, component_state["children"], *component_state["args"]
    )
