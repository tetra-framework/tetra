import os
import shutil
import sys
from typing import Generator, AsyncGenerator, Any

import pytest
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.sessions.backends.cache import SessionStore
from django.core.management import call_command
from django.http import HttpRequest
from django.test import RequestFactory
from playwright.sync_api import Page, Browser

from django.urls import reverse
from tetra.middleware import TetraDetails
from tetra import Library
from channels.testing import WebsocketCommunicator


BASE_DIR = Path(__file__).resolve().parent
# Ensure tests directory is importable (so `from utils import ...` and `from apps...` work)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


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
def tetra_component(page: Page, live_server):
    test_ui = Library("test_ui", "main")

    def _tetra_component(component_cls, **kwargs):
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

    return _tetra_component


def pytest_addoption(parser):
    """Looks for the `skip-slow` argument"""
    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="skip slow tests",
    )


def pytest_collection_modifyitems(config, items):
    """This skips the tests if skip-slow is present"""
    if config.getoption("--skip-slow"):
        skip_slow = pytest.mark.skip(reason="skip slow tests")
        for item in items:
            if "playwright" in item.keywords:
                item.add_marker(skip_slow)


@pytest.fixture(scope="session", autouse=True)
def setup_django_environment():
    """
    This fixture sets up the Django environment for the test session.
    It ensures that the temporary upload directory exists and then runs
    the 'tetrabuild' command.
    """
    # Ensure the temporary upload directory exists
    upload_dir = Path(settings.MEDIA_ROOT) / "tetra_temp_upload"
    os.makedirs(upload_dir, exist_ok=True)

    call_command("tetrabuild")


@pytest.fixture(autouse=True)
def cleanup_temp_uploads_and_media():
    """
    This fixture cleans up the temporary upload directory after each test.
    """
    yield
    temp_upload_dir = Path(settings.MEDIA_ROOT) / "tetra_temp_upload"
    if temp_upload_dir.exists():
        for item in temp_upload_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


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
def tetra_request() -> HttpRequest:
    """
    Returns an Http GET Request with a session, and a `tetra` attribute.
    """
    factory = RequestFactory()
    request = factory.get("/")

    add_session_to_request(request)

    request.tetra = TetraDetails(request)

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


@pytest.fixture(scope="function")
def page(browser: Browser) -> Generator[Page, Page, None]:
    context = browser.new_context()  # cheap, isolated
    page = context.new_page()
    # Here comes a fancy hack:
    # If debugging tests (e.g. using PyCharm, should work in VSCode too),
    # deactivate the timeout, as it makes breakpoints impossible to use. As default
    # else use 3s, this should suffice for even file uploads locally.
    page.set_default_timeout(1000 * 60 if "pydevd" in sys.modules else 3000)
    yield page
    context.close()


def pytest_configure(config):
    """Auto-add the slow mark to the config at runtime"""
    settings.configure(
        BASE_DIR=BASE_DIR,
        SECRET_KEY="django-insecure1234567890",
        ROOT_URLCONF="tests.urls",
        INSTALLED_APPS=[
            "tetra",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
            "django.contrib.sessions",
            "tests.apps.main",
            "tests.apps.another_app",
        ],
        MIDDLEWARE=[
            "django.middleware.security.SecurityMiddleware",
            "whitenoise.middleware.WhiteNoiseMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            "tetra.middleware.TetraMiddleware",
        ],
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
        },
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                # "DIRS": [BASE_DIR / "templates"],
                "APP_DIRS": True,
            },
        ],
        STATIC_URL="/static/",
        STATIC_ROOT=BASE_DIR / "staticfiles",
        MEDIA_ROOT=BASE_DIR / "media",
        DEBUG=True,
        # STORAGES={
        #     "staticfiles": {
        #         "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        #     },
        # },
        CHANNEL_LAYERS={
            "default": {
                "BACKEND": "channels.layers.InMemoryChannelLayer",
            },
        },
        FORMS_URLFIELD_ASSUME_HTTPS=True,
    )
    config.addinivalue_line("markers", "playwright: mark test as slow to run")
