import json
import uuid
import warnings
from urllib.parse import urlsplit, urlunsplit

from django.contrib.messages import get_messages
from django.contrib.messages.storage.base import Message
from django.http import HttpRequest, QueryDict, JsonResponse, FileResponse
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
    _url: str = ""

    # Based on HtmxDetails from htmx-django by adamchainz
    def __init__(self, request: HttpRequest) -> None:
        self.request = request
        self._url = self._get_header_value("T-Current-URL")

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
        return self._url

    # @cached_property
    # def new_url(self) -> str | None:
    #     return self._new_url if self._new_url else self.current_url

    @cached_property
    def current_url_abs_path(self) -> str | None:
        warnings.warn(
            "TetraDetails.current_url_abs_path is deprecated. Use TetraDetails.current_url_full_path instead.",
            DeprecationWarning,
        )
        return self.current_url_full_path

    @cached_property
    def current_url_full_path(self) -> str | None:
        """Returns the full path (including params) of the current URL in the
        browser.

        Example:
            When the browser URL is "https://example.com/foo/bar?baz=qux",
            current_url_path returns "/foo/bar?baz=qux".
        """
        url = self._url
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
    def current_url_path(self) -> str:
        """Returns the path part of the current URL in the browser, without params.

        Example:
            When the browser URL is "https://example.com/foo/bar?baz=qux",
            current_url_path returns "/foo/bar".
        """
        value = self._url
        if value is not None:
            # get the path component from the URL
            return urlsplit(value).path or ""
        return ""

    @cached_property
    def url_query_params(self) -> QueryDict:
        """Returns the query parameters of the current URL in the browser, as a QueryDict.

        Example:
            When the browser URL is "https://example.com/foo/bar?baz=qux",
            url_query_params returns QueryDict({'baz': ['qux']}), so you can easily
            access the query parameters using `url_query_params['baz']`.
        """
        split = urlsplit(self._url)
        if (
            split.scheme == self.request.scheme
            and split.netloc == self.request.get_host()
        ):
            return QueryDict(split.query)
        return QueryDict()

    def set_url_path(self, path: str) -> None:
        """Replace path part of new URL with given path."""
        split = urlsplit(self._url)
        if (
            split.scheme == self.request.scheme
            and split.netloc == self.request.get_host()
        ):
            self._url = str(urlunsplit(split._replace(path=path)))

    def set_url(self, url: str) -> None:
        """Set new internal URL.

        This is needed if the browser URL will change during the request, and this
        should be reflected in the request.tetra object.
        """
        self._url = url

    def set_url_query_param(self, param, value):
        """Set/replace a query parameter of the current URL in the browser,
        as a QueryDict.
        """
        split = urlsplit(self._url)
        if (
            split.scheme == self.request.scheme
            and split.netloc == self.request.get_host()
        ):
            query_dict = QueryDict(split.query, mutable=True)
            query_dict[param] = value
            # replace the params in the split url
            self._url = str(urlunsplit(split._replace(query=query_dict.urlencode())))


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

        if isinstance(response, FileResponse):
            return response

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
