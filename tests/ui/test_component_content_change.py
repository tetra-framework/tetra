import pytest
from django.urls import reverse

from tetra import Library, public, Component

lib = Library("ui", "main")


@lib.register
class ComponentWithButton(Component):

    text: str = "initial"

    @public
    def click(self):
        self.text = "changed"

    template = """
    <div> 
        <button id="click_button" @click="click()">
        Click Me
        </button>
        <div id="result">{{ text }}</div>
    <div>
    """


@pytest.mark.playwright
def test_component_click_content_change(page, live_server):
    """Tests component button click using playwright"""
    page.goto(live_server.url + reverse("component_with_button"))

    # # Check initial state
    result_div = page.locator("#result")
    assert result_div.text_content() == "initial"

    page.click("#click_button")
    page.wait_for_selector("#result")
    assert result_div.text_content() == "changed"


# ------------------- dynamic content return and variable change ------------------
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
def test_basic_component_return_value_changes_content_dynamically(page, live_server):
    """Tests a component that dynamically returns a value to the Js frontend,
    which updates the content dynamically with the return value"""
    page.goto(live_server.url + reverse("component_with_return_value"))

    button = page.locator("#clickme")
    assert button.text_content() == "Click me"
    button.click()
    result = page.wait_for_selector("#result")
    assert result.text_content() == "Hello, World!"
