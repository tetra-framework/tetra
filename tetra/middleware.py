from django.middleware.csrf import get_token
from .utils import render_scripts, render_styles


class TetraMiddlewareException(Exception):
    pass


def inline_script_tag(source):
    return f"<script>{source}</script>"


def inline_styles_tag(source):
    return f"<styles>{source}</styles>"


class TetraMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        csrf_token = get_token(request)
        response = self.get_response(request)

        if (
            "Content-Type" not in response.headers
            or "text/html" not in response.headers["Content-Type"]
        ):
            return response
        if int(response.status_code) >= 500:
            return response

        if hasattr(request, "tetra_components_used") and request.tetra_components_used:
            if not hasattr(request, "tetra_scripts_placeholder_string"):
                raise TetraMiddlewareException(
                    "The {% tetra_scripts %} tag is required to be placed in the "
                    "page's <head> tag when using Tetra components."
                )
            if not hasattr(request, "tetra_styles_placeholder_string"):
                raise TetraMiddlewareException(
                    "The {% tetra_styles %} tag is required to be placed in the page's "
                    "<head> tag when using Tetra components."
                )
            if request.tetra_scripts_placeholder_string not in response.content:
                raise TetraMiddlewareException(
                    "Placeholder from {% tetra_scripts %} not found."
                )
            if request.tetra_styles_placeholder_string not in response.content:
                raise TetraMiddlewareException(
                    "Placeholder from {% tetra_styles %} not found."
                )

            content = response.content
            content = content.replace(
                request.tetra_scripts_placeholder_string,
                render_scripts(request, csrf_token).encode(),
            )
            content = content.replace(
                request.tetra_styles_placeholder_string, render_styles(request).encode()
            )
            response.content = content

        return response
