import pytest
from django.urls import reverse

from tetra import Component, public, Library

lib = Library("ui", "main")


@lib.register
class ComponentWithMethodReturnValue(Component):
    msg = public("")

    @public
    def get_hello(self) -> str:
        # don't set the value directly, just return it
        return "Hello, World!"

    template = """<div id='component'>
    <button id="clickme" @click="msg=get_hello()">Click me</button>
    <div id="result" x-text="msg"></div>
    </div>"""


@pytest.mark.django_db
@pytest.mark.playwright
def test_basic_component_return(page, live_server):
    """Tests a simple component with / end"""
    page.goto(live_server.url + reverse("component_with_return_value"))

    button = page.locator("#clickme")
    assert button.text_content() == "Click me"
    button.click()
    result = page.wait_for_selector("#result")
    assert result.text_content() == "Hello, World!"
