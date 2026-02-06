import json
import logging

from django.http import HttpResponseNotFound, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from . import Library
from .utils import from_json, NamedTemporaryFileUploadHandler, request_id


logger = logging.getLogger(__name__)


@csrf_exempt
def component_method(request, *args, **kwargs):
    """Override default upload handlers, to create a "persistent" temporary file for
    file uploads that are done using Tetra methods."""
    request.upload_handlers = [NamedTemporaryFileUploadHandler(request)]
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

    # Allow special internal "_refresh" method for reactive component updates
    is_refresh = method_name == "_refresh"

    if not is_refresh and method_name not in (m["name"] for m in Component._public_methods):
        logger.warning(
            f"Tetra method was requested, but not found: {component_name}.{method_name}()"
        )
        return HttpResponseNotFound()

    try:
        # check if request includes multipart/form-data files
        if request.content_type == "multipart/form-data":
            payload = from_json(request.POST["tetra_payload"])
        # if the request is application-data/json, we need to decode it ourselves
        elif request.content_type == "application/json" and request.body:
            payload = from_json(request.body.decode())
        else:
            logger.error("Unsupported content type: %s", request.content_type)
            return HttpResponseBadRequest()

        # Extract request ID and store it in context variable
        if isinstance(payload, dict) and payload.get("id"):
            request_id.set(payload["id"])

        # Extract component state from unified protocol payload
        if (
            isinstance(payload, dict)
            and payload.get("protocol") == "tetra-1.0"
            and "payload" in payload
        ):
            inner_payload = payload["payload"]
            component_state = {
                "encrypted": inner_payload.get("encrypted_state"),
                "data": inner_payload.get("state"),
                "children": inner_payload.get("children_state"),
                "args": inner_payload.get("args"),
            }
            # Add files to the component state
            if request.content_type == "multipart/form-data":
                for key in request.FILES:
                    component_state["data"][key] = request.FILES[key]
        else:
            logger.error("Invalid or missing Tetra protocol in payload")
            return HttpResponseBadRequest()

    except (json.decoder.JSONDecodeError, KeyError) as e:
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

    # Handle special _refresh method by just rendering the component
    if is_refresh:
        from django.http import JsonResponse
        html = component.render()
        response_data = {
            "protocol": "tetra-1.0",
            "success": True,
            "payload": {
                "html": html
            },
            "metadata": {
                "js": [],
                "styles": [],
                "messages": [],
                "callbacks": []
            }
        }
        return JsonResponse(response_data)

    logger.debug(
        f"Calling component method {component.__class__.__name__}.{method_name}()"
    )
    return component._call_public_method(
        request, method_name, component_state["children"], *component_state["args"]
    )
