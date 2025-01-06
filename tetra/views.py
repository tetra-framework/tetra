import json
import logging

from django.http import HttpResponseNotFound, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from .component_register import libraries
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
        Component = libraries[app_name][library_name].components[component_name]
    except KeyError:
        return HttpResponseNotFound()

    if method_name not in (m["name"] for m in Component._public_methods):
        logger.warning(
            f"Tetra method was requested, but not found: {component_name}.{method_name}()"
        )
        return HttpResponseNotFound()

    # check if request is form data
    if request.content_type == "multipart/form-data":
        try:
            data = from_json(request.POST["state"])
            if "args" not in data:
                data["args"] = []
            data["args"].extend(request.FILES.values())
        except json.decoder.JSONDecodeError as e:
            logger.error(e)
            return HttpResponseBadRequest()
    else:
        try:
            data = from_json(request.body.decode())

        except json.decoder.JSONDecodeError as e:
            logger.error(e)
            return HttpResponseBadRequest()

    if not (
        isinstance(data, dict) and "args" in data and isinstance(data["args"], list)
    ):
        raise TypeError("Invalid Args value.")

    if not hasattr(request, "tetra_components_used"):
        request.tetra_components_used = set()
    request.tetra_components_used.add(Component)

    component = Component.from_state(data, request)
    logger.debug(
        f"Calling component method {component.__class__.__name__}.{method_name}()"
    )
    return component._call_public_method(
        request, method_name, data["children"], *data["args"]
    )
