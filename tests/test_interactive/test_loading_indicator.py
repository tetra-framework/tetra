import time
import pytest
from django.urls import reverse
from playwright.sync_api import Page
from tetra import Library, public, Component

ui = Library("ui", "main")


@ui.register
class LoadingIndicatorComponent(Component):
    @public
    def slow_method(self):
        time.sleep(1)
        return "Done"

    template = """
    <div>
        <button id="slow_button" @click="slow_method()" t-indicator="#spinner">
            Click Me
        </button>
        <span id="spinner">Spinner</span>
    </div>
    """


@pytest.mark.playwright
def test_loading_indicator(component_locator):

    component = component_locator(LoadingIndicatorComponent)

    spinner = component.locator("#spinner")
    button = component.locator("#slow_button")

    # Initial state: hidden
    assert spinner.is_hidden()
    # It should have the tetra-indicator class
    assert "tetra-indicator" in (spinner.get_attribute("class") or "")

    # Click and check during request
    button.click(no_wait_after=True)

    # Wait for the spinner to be visible
    component.locator("#spinner:not([hidden])").wait_for(state="visible")
    assert spinner.is_visible()
    classes = component.evaluate('document.getElementById("slow_button").className')
    for c in classes.split():
        assert "tetra-request" in classes

    classes = component.evaluate('document.getElementById("spinner").className')
    for c in classes.split():
        assert c.startswith("tetra-indicator-")  # tetra-indicator-235678872t578

    # Wait for completion (slow_method takes 1s)
    component.locator("#spinner").wait_for(state="hidden", timeout=5000)
    assert spinner.is_hidden()
    classes = component.evaluate('document.getElementById("spinner").className')
    assert "tetra-request" not in classes
