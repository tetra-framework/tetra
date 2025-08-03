import json

from bs4 import BeautifulSoup, Tag
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.cache import SessionStore
from django.test import RequestFactory

from tetra.views import _component_method


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


def extract_component_tag(html: str | bytes) -> Tag:
    """Helper to extract the `div#component` content from the given HTML as
    BeautifulSoup parsed entity."""
    return BeautifulSoup(html, features="html.parser").html.body.find(id="component")


def call_component_method(
    app_name,
    library_name,
    component_name,
    method,
    *args,
    **kwargs,
):
    factory = RequestFactory(content_type="application/json")
    component_state = {
        "csrfmiddlewaretoken": "fake-token",
        "args": [],
        "encrypted": "",  # FIXME: test does not work with invalid encrypted state
        "data": {"data": ""},
    }
    req = factory.post(
        "/", json.dumps(component_state), content_type="application/json"
    )

    req.session = SessionStore()
    req.session.create()
    req.user = AnonymousUser()
    req.csrf_processing_done = True
    return _component_method(req, library_name, component_name, method)
