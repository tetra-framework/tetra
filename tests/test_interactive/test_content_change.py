import pytest
from django.urls import reverse
from playwright.sync_api import Page

from tetra import Library, public, Component

ui = Library("ui", "main")


@ui.register
class ComponentWithButton(Component):

    text: str = "initial"

    @public
    def click(self):
        self.text = "changed"

    # language=html
    template = """
    <div> 
        <button id="click_button" @click="click()">
        Click Me
        </button>
        <div id="result">{{ text }}</div>
    <div>
    """


@pytest.mark.playwright
def test_component_click_content_change(component_locator):
    """Tests component button click using playwright"""
    component = component_locator(ComponentWithButton)

    # # Check initial state
    result_div = component.locator("#result")
    assert result_div.text_content() == "initial"

    component.locator("#click_button").click()
    result_div = component.locator("#result")
    result_div.wait_for(state="visible")
    assert result_div.text_content() == "changed"


# ------------------- dynamic content return and variable change ------------------


@ui.register
class ComponentWithMethodReturnValue(Component):
    msg = public("")

    @public
    def get_hello(self) -> str:
        # don't set the value directly, just return it
        return "Hello, World!"

    # language=html
    template = """<div id='component'>
    <button id="clickme" @click="msg=get_hello()">Click me</button>
    <div id="result" x-text="msg"></div>
    </div>"""


@pytest.mark.playwright
def test_basic_component_return_value_changes_content_dynamically(component_locator):
    """Tests a component that dynamically returns a value to the Js frontend,
    which updates the content dynamically with the return value"""
    component = component_locator(ComponentWithMethodReturnValue)
    button = component.locator("#clickme")
    assert button.text_content() == "Click me"
    button.click()
    result = component.locator("#result")
    result.wait_for(state="visible")
    assert result.text_content() == "Hello, World!"
