import json
import uuid
from urllib.parse import urlsplit, urlunsplit

from django.contrib.messages import get_messages
from django.contrib.messages.storage.base import Message
from django.http import HttpRequest, QueryDict
from django.middleware.csrf import get_token
from django.utils.functional import cached_property

from .utils import render_scripts, render_styles, TetraJSONEncoder
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


class TetraMiddleware:
    async_capable = True
    sync_capable = False

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    async def __call__(self, request):
        csrf_token = get_token(request)
        request.tetra = TetraDetails(request)
        response = await self.get_response(request)
        messages: list[Message] = []

        for message in get_messages(request):
            # FIXME: maybe use a more efficient data structure for large number of
            #  messages

            # monkey patch an uid into the Message class to ensure it has a unique ID
            # if it doesn't have one already
            if not hasattr(message, "uid"):
                message.uid = str(uuid.uuid4())
            messages.append(message)
        if messages:
            # Put the messages list into the T-Messages header
            response.headers["T-Messages"] = json.dumps(messages, cls=TetraJSONEncoder)

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
