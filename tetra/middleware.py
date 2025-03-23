from typing import Callable, Awaitable
from urllib.parse import urlsplit, urlunsplit

from django.http import HttpRequest, HttpResponseBase, QueryDict
from django.middleware.csrf import get_token
from django.utils.functional import cached_property

from .utils import render_scripts, render_styles
from asgiref.sync import iscoroutinefunction, markcoroutinefunction


class TetraMiddlewareException(Exception):
    pass


class TetraHttpRequest(HttpRequest):
    """This is just a dummy HttpRequest subclass that has a tetra attribute.

    This mainly exists so that the `request` attribute of components contains a
    `tetra` attribute, so IDEs can improve autocompletion. In fact, the `request`
    attribute is a WsgiRequest or `AsgiRequest` object.
    """

    tetra: "TetraDetails"


def inline_script_tag(source) -> str:
    return f"<script>{source}</script>"


def inline_styles_tag(source) -> str:
    return f"<styles>{source}</styles>"


class TetraMiddleware:
    """Middleware that modifies the request with helpers."""

    # Some code is borrowed from adamchainz' django-htmx
    async_capable = True
    sync_capable = False

    def __init__(
        self,
        get_response: (
            Callable[[HttpRequest], HttpResponseBase]
            | Callable[[HttpRequest], Awaitable[HttpResponseBase]]
        ),
    ) -> None:
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)
        self.async_mode = iscoroutinefunction(self.get_response)

        if self.async_mode:
            # Mark the class as async-capable, but do the actual switch
            # inside __call__ to avoid swapping out dunder methods
            markcoroutinefunction(self)

    def replace_tetra_components_used(self, request, response, csrf_token):
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

    def check_content_type(self, response) -> bool:
        if (
            "Content-Type" not in response.headers
            or "text/html" not in response.headers["Content-Type"]
        ):
            return False
        if int(response.status_code) >= 500:
            return False
        return True

    def __call__(self, request):
        if self.async_mode:
            return self.__acall__(request)

        csrf_token = get_token(request)
        response = self.get_response(request)
        request.tetra = TetraDetails(request)
        if not self.check_content_type(response):
            return response

        self.replace_tetra_components_used(request, response, csrf_token)
        return response

    async def __acall__(self, request) -> HttpResponseBase:
        request.tetra = TetraDetails(request)
        response = await self.get_response(request)
        csrf_token = get_token(request)
        if not self.check_content_type(response):
            return response

        self.replace_tetra_components_used(request, response, csrf_token)

        return response


class TetraDetails:
    # Based on HtmxDetails from htmx-django by adamchainz
    def __init__(self, request: HttpRequest) -> None:
        self.request = request

    def _get_header_value(self, name: str) -> str | None:
        value = self.request.headers.get(name) or None
        # if value:
        #     if self.request.headers.get(f"{name}-URI-AutoEncoded") == "true":
        #         value = unquote(value)
        return value

    def __bool__(self) -> bool:
        """returns True if 'T-Request' header is present and true, else False."""
        return self._get_header_value("T-Request") == "true"

    @cached_property
    def current_url(self) -> str | None:
        return self._get_header_value("T-Current-URL")

    @cached_property
    def current_url_abs_path(self) -> str | None:
        url = self.current_url
        if url is not None:
            split = urlsplit(url)
            if (
                split.scheme == self.request.scheme
                and split.netloc == self.request.get_host()
            ):
                url = str(urlunsplit(split._replace(scheme="", netloc="")))

            else:
                url = None
        return url

    @cached_property
    def url_query_params(self) -> QueryDict:
        split = urlsplit(self.current_url)
        if (
            split.scheme == self.request.scheme
            and split.netloc == self.request.get_host()
        ):
            return QueryDict(split.query)
        return QueryDict()
