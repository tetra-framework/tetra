from channels.testing import WebsocketCommunicator
from django.apps import apps
from django.http import HttpRequest
from django.test import RequestFactory
from typing import AsyncGenerator, Any

import pytest
from django.urls import reverse
from django.contrib.sessions.backends.cache import SessionStore
from playwright.sync_api import Page

from tetra import Library
from tetra.components.base import BasicComponent
from tetra.middleware import TetraDetails

# These pytest fixtures may be usable in apps that use Tetra, so they are provided in a
# separate `fixtures` module that can be imported in your conftest.py


def add_session_to_request(request: HttpRequest) -> HttpRequest:
    """
    Helper to add a session to a factory request
    """
    from django.contrib.auth.models import AnonymousUser

    request.session = SessionStore()
    request.session.create()
    request.user = AnonymousUser()
    return request


@pytest.fixture
def post_request_with_session():
    """
    Returns an Http GET Request with a session, and a `tetra` attribute.
    """
    factory = RequestFactory()
    request = factory.post("/")  # Create a request object

    add_session_to_request(request)

    return request


@pytest.fixture
def current_app():
    return apps.get_app_config("main")


@pytest.fixture
def component_locator(page: Page, live_server):
    """This fixture is a helper that renders and locates your component in
    playwright.

    Use it in conjunction with tetra.tests.views.render_component_view and make sure
    your tests' urls.py includes a line like:

    ```python
    urlpatterns = [ path("", include("tetra.tests.urls")) ]
    ```
    """
    test_ui = Library("test_ui", "main")

    def _component_locator(component_cls, **kwargs):
        if not hasattr(component_cls, "_library") or component_cls._library is None:
            component_cls = test_ui.register(component_cls)
            test_ui.build()
        else:
            # ensure the library is built if it hasn't been yet
            # (though normally libraries registered at module level are built by tetrabuild)
            pass

        library = component_cls._library
        component_name = component_cls.__name__
        full_component_name = component_cls.full_component_name()

        component_tag = f"{{% {library.name}.{component_name} "
        for key, value in kwargs.items():
            component_tag += f'{key}="{value}" '
        component_tag += "/ %}"

        page.goto(
            live_server.url
            + reverse("render_component_view")
            + f"?component_tag={component_tag}"
        )
        return page.locator(f'[tetra-component="{full_component_name}"]')

    return _component_locator


@pytest.fixture
async def tetra_ws_communicator(db) -> AsyncGenerator[WebsocketCommunicator, Any]:
    """
    Returns a WebsocketCommunicator for TetraConsumer with a valid session and
    AnonymousUser, and closes it after usage.
    """
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.sessions.backends.db import SessionStore
    from tetra.consumers import TetraConsumer

    session = SessionStore()
    session.create()

    scope = {
        "type": "websocket",
        "session": session,
        "user": AnonymousUser(),
        "path": "/ws/tetra/",
    }

    communicator = WebsocketCommunicator(
        TetraConsumer.as_asgi(),
        "/ws/tetra/",
    )
    communicator.scope.update(scope)
    connected, _ = await communicator.connect()
    assert connected
    yield communicator
    await communicator.disconnect()


@pytest.fixture
def component_render(client):
    """Fixture that renders a component class for testing"""
    test_ui = Library("test_ui", "main")

    def _component_render(component_cls: type[BasicComponent], **kwargs):
        if not hasattr(component_cls, "_library") or component_cls._library is None:
            component_cls = test_ui.register(component_cls)
            test_ui.build()
        else:
            # ensure the library is built if it hasn't been yet
            # (though normally libraries registered at module level are built by tetrabuild)
            pass

        library = component_cls._library
        component_name = component_cls.__name__
        full_component_name = component_cls.full_component_name()

        component_tag = f"{{% {library.name}.{component_name} "
        for key, value in kwargs.items():
            component_tag += f'{key}="{value}" '
        component_tag += "/ %}"

        return client.get(
            reverse("render_component_view") + f"?component_tag={component_tag}"
        )

    return _component_render


@pytest.fixture
def tetra_request() -> HttpRequest:
    """
    Returns an Http GET Request with a session, and a `tetra` attribute.
    """
    factory = RequestFactory()
    request = factory.get("/")

    add_session_to_request(request)

    request.tetra = TetraDetails(request)

    return request
