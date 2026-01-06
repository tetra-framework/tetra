import os
import shutil
import sys
from typing import Generator

import pytest
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from playwright.sync_api import Page, Browser

from tetra.tests.fixtures import (  # type: ignore[unused-import]
    tetra_request,
    tetra_ws_communicator,
    component_render,
    component_locator,
    add_session_to_request,
    current_app,
    post_request_with_session,
)

BASE_DIR = Path(__file__).resolve().parent
# Ensure tests directory is importable (so `from utils import ...` and `from apps...` work)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


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
        ROOT_URLCONF="urls",
        INSTALLED_APPS=[
            "tetra",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
            "django.contrib.sessions",
            "apps.main",
            "apps.another_app",
        ],
        MIDDLEWARE=[
            "django.middleware.security.SecurityMiddleware",
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
        CHANNEL_LAYERS={
            "default": {
                "BACKEND": "channels.layers.InMemoryChannelLayer",
            },
        },
    )
    config.addinivalue_line("markers", "playwright: mark test as slow to run")
