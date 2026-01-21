import pytest
from playwright.sync_api import Page
from tetra import Library, public, Component

ui = Library("ui", "main")


@ui.register
class StoreComponent(Component):
    # theme is synced with Alpine.store('settings').theme
    theme = public("light").store("settings.theme")

    @public
    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"

    # language=html
    template = """
    <div id="component">
        <div id="theme-display" x-text="theme">Initial Theme</div>
        <button id="toggle-btn" @click="toggle_theme()">Toggle Theme</button>
    </div>
    """


@pytest.mark.playwright
def test_store_sync_backend_to_frontend(component_locator, page: Page):
    """Test that changing a value on the backend updates the Alpine store."""
    component = component_locator(StoreComponent)

    # Initial state
    page.wait_for_timeout(1000)
    # Check if component data exists
    assert (
        page.evaluate("Alpine.$data(document.querySelector('#component')).theme")
        == "light"
    )

    # Click toggle button (calls backend method)
    component.locator("#toggle-btn").click()

    # Wait for update
    page.wait_for_timeout(1000)

    # Check store value via JS
    assert page.evaluate("Alpine.store('settings').theme") == "dark"


@pytest.mark.playwright
def test_store_sync_frontend_to_backend(component_locator, page: Page):
    """Test that changing the Alpine store updates the component property."""
    component = component_locator(StoreComponent)

    # Initial state
    page.wait_for_timeout(1000)
    assert (
        page.evaluate("Alpine.$data(document.querySelector('#component')).theme")
        == "light"
    )

    # Update store directly in JS
    page.evaluate("Alpine.store('settings').theme = 'dark'")

    # Wait for component data to update
    page.wait_for_timeout(1000)
    assert (
        page.evaluate("Alpine.$data(document.querySelector('#component')).theme")
        == "dark"
    )

    # Now verify it's synced back to backend by calling a method and seeing it persist
    # If we toggle again via backend, it should go from dark -> light
    component.locator("#toggle-btn").click()

    page.wait_for_timeout(1000)
    # Check both store and component data
    assert page.evaluate("Alpine.store('settings').theme") == "light"
    assert (
        page.evaluate("Alpine.$data(document.querySelector('#component')).theme")
        == "light"
    )


@ui.register
class NestedStoreComponent(Component):
    val = public("orig").store("myapp.settings.nested.value")

    @public
    def set_val(self, new_val):
        self.val = new_val

    # language=html
    template = """
    <div id="nested-component">
        <div id="val-display" x-text="val">Initial Val</div>
        <button id="set-btn" @click="set_val('new-val')">Set Val</button>
    </div>
    """


@pytest.mark.playwright
def test_nested_store_sync(component_locator, page: Page):
    """Test syncing with a nested store property."""
    component = component_locator(NestedStoreComponent)

    # Initial state
    page.wait_for_timeout(1000)
    assert page.evaluate("Alpine.store('myapp').settings.nested.value") == "orig"

    component.locator("#set-btn").click()

    # Wait for update
    page.wait_for_timeout(1000)
    assert page.evaluate("Alpine.store('myapp').settings.nested.value") == "new-val"


@ui.register
class MultiComponentStoreA(Component):
    val = public("initialA").store("shared.val")
    # language=html
    template = '<div id="compA" x-text="val"></div>'


@ui.register
class MultiComponentStoreB(Component):
    val = public("initialB").store("shared.val")
    # language=html
    template = '<div id="compB" x-text="val"></div>'


@pytest.mark.playwright
def test_multi_component_store_init(page: Page, live_server):
    """Test how multiple components with different init values handle a shared store."""
    from django.urls import reverse

    component_tag = "{% ui.MultiComponentStoreA / %}{% ui.MultiComponentStoreB / %}"

    page.goto(
        live_server.url
        + reverse("render_component_view")
        + f"?component_tag={component_tag}"
    )

    page.wait_for_timeout(1000)

    valA = page.evaluate("Alpine.$data(document.querySelector('#compA')).val")
    valB = page.evaluate("Alpine.$data(document.querySelector('#compB')).val")
    storeVal = page.evaluate("Alpine.store('shared').val")

    print(f"DEBUG: valA={valA}, valB={valB}, storeVal={storeVal}")

    # They should be synced
    assert valA == valB == storeVal
    # We need to decide what the expected value is.
    # Current implementation:
    # compA inits -> store.val = "initialA"
    # compB inits -> initialStoreVal is "initialA" -> compB.val = "initialA"
    # So "initialA" should win.
    assert storeVal == "initialA"
