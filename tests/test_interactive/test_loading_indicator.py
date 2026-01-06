import time
import pytest
from tetra import Library, public, Component

ui = Library("ui", "main")


@ui.register
class ConcurrentLoadingIndicatorComponent(Component):
    """Component with 2 buttons that share a loading indicator. Both buttons trigger
    slow methods, but with different durations."""

    @public
    def slow_method_1(self):
        time.sleep(1)
        return "Done 1"

    @public
    def slow_method_2(self):
        time.sleep(2)
        return "Done 2"

    template = """
    <div>
        <button id="button_1" @click="slow_method_1()" t-indicator="#spinner">
            Click 1
        </button>
        <button id="button_2" @click="slow_method_2()" t-indicator="#spinner">
            Click 2
        </button>
        <span id="spinner" hidden>Spinner</span>
    </div>
    """


@pytest.mark.playwright
def test_loading_indicator(component_locator):

    component = component_locator(ConcurrentLoadingIndicatorComponent)

    spinner = component.locator("#spinner")
    button = component.locator("#button_1")

    # Initial state: hidden
    assert spinner.is_hidden()
    # It should have the tetra-indicator class
    assert "tetra-indicator" in (spinner.get_attribute("class") or "")

    # Click and check during request
    button.click(no_wait_after=True)

    # Wait for the spinner to be visible
    component.locator("#spinner:not([hidden])").wait_for(state="visible")
    assert spinner.is_visible()
    classes = component.evaluate('document.getElementById("button_1").className')
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


@pytest.mark.playwright
def test_concurrent_loading_indicators(page, component_locator):
    component = component_locator(ConcurrentLoadingIndicatorComponent)

    spinner = component.locator("#spinner")
    button_1 = component.locator("#button_1")
    button_2 = component.locator("#button_2")

    # Initial state: hidden
    assert spinner.is_hidden()

    # Click first button
    button_1.click(no_wait_after=True)
    component.locator("#spinner:not([hidden])").wait_for(state="visible")
    assert spinner.is_visible()

    # Click second button
    button_2.click(no_wait_after=True)

    # Wait a bit for the first request to finish (approx 1s)
    # But first, ensure both buttons have tetra-request class
    assert "tetra-request" in (button_1.get_attribute("class") or "")
    assert "tetra-request" in (button_2.get_attribute("class") or "")

    # Wait for the first button to finish its request
    component.locator("#button_1:not(.tetra-request)").wait_for(
        state="visible", timeout=3000
    )

    # THIS IS THE IMPORTANT PART: The spinner might be hidden now because the first
    # request is finished
    assert (
        spinner.is_visible()
    ), "Spinner should still be visible because second request is in flight"

    assert "tetra-request" in (button_2.get_attribute("class") or "")

    # Wait for second button to finish
    component.locator("#button_2:not(.tetra-request)").wait_for(
        state="visible", timeout=3500
    )
    # Then, the spinner must be hidden
    assert spinner.is_hidden()
