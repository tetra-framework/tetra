import pytest
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.sessions.backends.cache import SessionStore
from django.core.management import call_command
from django.test import RequestFactory
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from tetra.middleware import TetraDetails

BASE_DIR = Path(__file__).resolve().parent


@pytest.fixture(scope="session", autouse=True)
def setup_django_environment():
    # Call your `tetrabuild` command before running tests - to make sure the Js
    # scripts and CSS files are built.
    call_command("tetrabuild")


@pytest.fixture
def tetra_request():
    factory = RequestFactory()
    req = factory.get("/")
    req.tetra = TetraDetails(req)
    return req


@pytest.fixture
def request_with_session():
    """Fixture to provide an Http GET Request with a session."""
    from django.contrib.auth.models import AnonymousUser

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


@pytest.fixture(scope="module")
def driver():
    options = Options()
    options.add_argument("--headless")
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(
        options=options,
    )
    yield driver
    driver.quit()


def pytest_configure():
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
        STORAGES={
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
            },
        },
    )
