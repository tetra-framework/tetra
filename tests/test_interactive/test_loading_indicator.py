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
def test_loading_indicator(page: Page, live_server):
    page.goto(
        live_server.url
        + reverse("generic_ui_component_test_view", args=["LoadingIndicatorComponent"])
    )

    spinner = page.locator("#spinner")
    button = page.locator("#slow_button")

    # Initial state: hidden
    assert spinner.is_hidden()
    # It should have the tetra-indicator class
    assert "tetra-indicator" in (spinner.get_attribute("class") or "")

    # Click and check during request
    button.click(no_wait_after=True)

    # Wait for the spinner to be visible
    page.wait_for_selector("#spinner:not([hidden])")
    assert spinner.is_visible()
    classes = page.evaluate('document.getElementById("slow_button").className')
    for c in classes.split():
        assert "tetra-request" in classes

    classes = page.evaluate('document.getElementById("spinner").className')
    for c in classes.split():
        assert c.startswith("tetra-indicator-")  # tetra-indicator-235678872t578

    # Wait for completion (slow_method takes 1s)
    page.wait_for_selector("#spinner", state="hidden", timeout=5000)
    assert spinner.is_hidden()
    classes = page.evaluate('document.getElementById("spinner").className')
    assert "tetra-request" not in classes
