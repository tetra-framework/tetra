import pytest
from pathlib import Path

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management import call_command

BASE_DIR = Path(__file__).resolve().parent


@pytest.fixture(scope="session", autouse=True)
def setup_django_environment():
    # Call your `tetrabuild` command before running tests - to make sure the Js
    # scripts and CSS files are built.
    call_command("tetrabuild")


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
            "tests.main",
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


def extract_component(html: str | bytes, innerHTML=True) -> str:
    """Helper to extract the `div#component` content from the given HTML.
    Also cuts out ALL newlines from the output.
    if innerHTML is False, it will return the outerHTML, including the HTML tag and
    attributes. If False, it returns only the inner content.
    """
    el = BeautifulSoup(html, features="html.parser").html.body.find(id="component")
    if innerHTML:
        return el.decode_contents().replace("\n", "")
    else:
        return str(el).replace("\n", "")
