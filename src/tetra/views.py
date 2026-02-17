import json
import logging

from django.http import (
    HttpResponseNotFound,
    HttpResponseBadRequest,
    HttpResponse,
    JsonResponse,
)
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from . import Library
from .utils import from_json, NamedTemporaryFileUploadHandler, request_id
from .exceptions import StaleComponentStateError


logger = logging.getLogger(__name__)


@csrf_exempt
def component_method(request, *args, **kwargs):
    """Override default upload handlers, to create a "persistent" temporary file for
    file uploads that are done using Tetra methods."""
    request.upload_handlers = [NamedTemporaryFileUploadHandler(request)]
    return _component_method(request, *args, **kwargs)


@csrf_protect
def _component_method(request) -> HttpResponse:
    if not request.method == "POST":
        return HttpResponseBadRequest()

    # Extract component and method info from the JSON payload
    try:
        # check if request includes multipart/form-data files
        if request.content_type.startswith("multipart/form-data"):
            payload = from_json(request.POST["tetra_payload"])
        # if the request is application/json, we need to decode it ourselves
        elif request.content_type.startswith("application/json") and request.body:
            payload = from_json(request.body.decode())
        else:
            logger.error("Unsupported content type: %s", request.content_type)
            return HttpResponseBadRequest()

        # Extract request ID and store it in context variable
        if isinstance(payload, dict) and payload.get("id"):
            request_id.set(payload["id"])

        # Validate protocol and extract payload
        if not (
            isinstance(payload, dict)
            and payload.get("protocol") == "tetra-1.0"
            and "payload" in payload
        ):
            logger.error("Invalid or missing Tetra protocol in payload")
            return HttpResponseBadRequest()

        inner_payload = payload["payload"]

        # Extract component location from payload
        app_name = inner_payload.get("app_name")
        library_name = inner_payload.get("library_name")
        component_name = inner_payload.get("component_name")
        method_name = inner_payload.get("method")

        if not all([app_name, library_name, component_name, method_name]):
            logger.error("Missing component or method information in payload")
            return HttpResponseBadRequest()

    except (json.decoder.JSONDecodeError, KeyError) as e:
        logger.error(e)
        return HttpResponseBadRequest()

    try:
        Component = Library.registry[app_name][library_name].components[component_name]
    except KeyError:
        return HttpResponseNotFound()

    # Allow special internal "_refresh" method for reactive component updates
    is_refresh = method_name == "_refresh"

    if not is_refresh and method_name not in (
        m["name"] for m in Component._public_methods
    ):
        logger.warning(
            f"Tetra method was requested, but not found: {component_name}.{method_name}()"
        )
        return HttpResponseNotFound()

    # Extract component state from payload (already parsed above)
    component_state = {
        "encrypted": inner_payload.get("encrypted_state"),
        "data": inner_payload.get("state"),
        "children": inner_payload.get("children_state"),
        "args": inner_payload.get("args"),
    }
    # Add files to the component state
    if request.content_type.startswith("multipart/form-data"):
        for key in request.FILES:
            component_state["data"][key] = request.FILES[key]

    if not (
        isinstance(component_state, dict)
        and "args" in component_state
        and isinstance(component_state["args"], list)
    ):
        raise TypeError("Invalid component state args.")

    if not hasattr(request, "tetra_components_used"):
        request.tetra_components_used = set()
    request.tetra_components_used.add(Component)

    try:
        component = Component.from_state(component_state, request)
    except StaleComponentStateError as e:
        # Component state references data that no longer exists
        logger.warning(f"Stale component state detected for {component_name}: {e}")
        return JsonResponse(
            {
                "protocol": "tetra-1.0",
                "type": "call.response",
                "success": False,
                "error": {
                    "code": "StaleComponentState",
                    "message": (
                        "This component's data is no longer valid. "
                        "It may have been deleted or modified by another user."
                    ),
                },
            },
            status=410,  # 410 Gone - resource no longer available
        )

    # Handle special _refresh method by just rendering the component
    if is_refresh:
        html = component.render()
        response_data = {
            "protocol": "tetra-1.0",
            "success": True,
            "payload": {"html": html},
            "metadata": {"js": [], "styles": [], "messages": [], "callbacks": []},
        }
        return JsonResponse(response_data)

    logger.debug(
        f"Calling component method {component.__class__.__name__}.{method_name}() "
        f"on component ID{component.component_id}"
    )
    return component._call_public_method(
        request, method_name, component_state["children"], *component_state["args"]
    )
