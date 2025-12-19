import os

import pytest
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.sessions.backends.cache import SessionStore
from django.core.management import call_command
from django.test import RequestFactory
from tetra.middleware import TetraDetails


BASE_DIR = Path(__file__).resolve().parent
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


def pytest_addoption(parser):
    """Looks for the `runplaywright` argument"""
    parser.addoption(
        "--runplaywright",
        action="store_true",
        default=False,
        help="run playwright tests",
    )


def pytest_collection_modifyitems(config, items):
    """This skips the tests if runslow is not present"""
    return
    if config.getoption("--runplaywright"):
        return
    skip_slow = pytest.mark.skip(reason="need --runplaywright option to run")
    for item in items:
        if "playwright" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture(scope="session", autouse=True)
def setup_django_environment():
    # Call your `tetrabuild` command before running tests - to make sure the Js
    # scripts and CSS files are built.
    call_command("tetrabuild")


@pytest.fixture
def tetra_request():
    from django.contrib.auth.models import AnonymousUser

    factory = RequestFactory()
    req = factory.get("/")

    req.session = SessionStore()
    req.session.create()

    req.user = AnonymousUser()
    req.tetra = TetraDetails(req)

    return req


@pytest.fixture
def request_with_session():
    """Fixture to provide an Http GET Request with a session."""
    from django.contrib.auth.models import AnonymousUser
    from tetra.middleware import TetraDetails

    factory = RequestFactory()
    req = factory.get("/")  # Create a request object

    req.session = SessionStore()
    req.session.create()
    req.user = AnonymousUser()
    req.tetra = TetraDetails(req)

    return req


@pytest.fixture
def post_request_with_session():
    """Fixture to provide a Http POST Request with a session."""
    from django.contrib.auth.models import AnonymousUser

    factory = RequestFactory()
    req = factory.post("/")  # Create a request object

    req.session = SessionStore()
    req.session.create()
    req.user = AnonymousUser()

    return req


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
    page.set_default_timeout(0 if "pydevd" in sys.modules else 3000)
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
            "tests.main",
            "tests.another_app",
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
