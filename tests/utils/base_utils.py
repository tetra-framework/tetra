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
    # Create unified protocol request envelope
    request_envelope = {
        "protocol": "tetra-1.0",
        "id": "test-req-id",
        "type": "call",
        "payload": {
            "component_id": "test-comp-id",
            "method": method,
            "args": [],
            "state": {"data": ""},
            "encrypted_state": "",  # FIXME: test does not work with invalid encrypted state
            "children_state": [],
            # Add component location metadata
            "app_name": app_name,
            "library_name": library_name,
            "component_name": component_name,
        },
    }
    req = factory.post(
        "/tetra/call/", json.dumps(request_envelope), content_type="application/json"
    )

    req.session = SessionStore()
    req.session.create()
    req.user = AnonymousUser()
    req.csrf_processing_done = True
    return _component_method(req)
