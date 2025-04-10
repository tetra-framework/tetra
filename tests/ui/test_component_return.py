import json

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.cache import SessionStore
from django.test import RequestFactory
from django.urls import reverse

from tetra import Component, public, Library
from tetra.views import _component_method
from selenium.webdriver.common.by import By


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
    return _component_method(req, app_name, library_name, component_name, method)


lib = Library("default", "main")


@lib.register
class ComponentWithMethodReturnValue(Component):
    msg = public("")

    @public
    def get_hello(self) -> str:
        # don't set the value directly, just return it
        return "Hello, World!"

    template = """<div id='component'>
    <button id="clickme" @click="msg=get_hello()">clickme</button>
    <div id="result" x-text="msg"></div>
    </div>"""


@pytest.mark.django_db
# FIXME: return values are difficult to test...
def test_basic_component_return(post_request_with_session, driver, live_server):
    """Tests a simple component with / end"""
    driver.get(live_server.url + reverse("component_with_return_value"))
    button = driver.find_element(By.ID, "clickme")
    assert driver.find_element(By.ID, "result").text == ""
    button.click()
    assert driver.find_element(By.ID, "result").text == "Hello, World!"
    pass
