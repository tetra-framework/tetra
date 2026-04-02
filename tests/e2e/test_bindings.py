import pytest
from playwright.sync_api import Page, expect

from tetra import Component, Library, public

ui = Library("ui", "main")


@ui.register
class BindingSearch(Component):
    query = public("")
    result = public("")

    @public
    def search(self):
        self.result = f"Found: {self.query}"

    template = """
    <div class="card">
        <h4>Child</h4>
        <input id="child-input" x-model="query" @input="search()">
        <span id="child-result" x-text="result"></span>
    </div>
    """


@ui.register
class BindingParent(Component):
    search_result = public("")

    template = """
    <div class="card">
        <h3>Parent: <span id="parent-result" x-text="search_result"></span></h3>
        {% ui.BindingSearch :result=search_result / %}
    </div>
    """


@pytest.mark.playwright
def test_binding_child_to_parent(page: Page, component_locator):
    """When child's 'result' changes via server method, parent's 'search_result'
    should update via the two-way binding."""
    component = component_locator(BindingParent)

    child_input = component.locator("#child-input")
    child_result = component.locator("#child-result")
    parent_result = component.locator("#parent-result")

    # Initial state
    expect(parent_result).to_have_text("")

    # Type in child input to trigger search via @input
    child_input.press_sequentially("hello", delay=50)

    # Wait for child to update from server
    expect(child_result).to_have_text("Found: hello", timeout=5000)

    # Parent should also be updated via binding
    expect(parent_result).to_have_text("Found: hello", timeout=5000)


@pytest.mark.playwright
def test_binding_parent_to_child(page: Page, component_locator):
    """Verify binding also works parent→child direction: when parent's attribute
    is set via a server method, child's bound attribute updates too."""
    component = component_locator(BindingParentWithClear)

    child_input = component.locator("#child-input")
    child_result = component.locator("#child-result")
    parent_result = component.locator("#parent-result")
    clear_btn = component.locator("#clear-btn")

    # First, trigger a search so both have values
    child_input.press_sequentially("test", delay=50)
    expect(child_result).to_have_text("Found: test", timeout=5000)
    expect(parent_result).to_have_text("Found: test", timeout=5000)

    # Clear from parent side
    clear_btn.click()

    # Both parent and child should be cleared
    expect(parent_result).to_have_text("", timeout=5000)
    expect(child_result).to_have_text("", timeout=5000)


@ui.register
class BindingParentWithClear(Component):
    search_result = public("")

    @public
    def clear(self):
        self.search_result = ""

    template = """
    <div class="card">
        <h3>Parent: <span id="parent-result" x-text="search_result"></span></h3>
        <button id="clear-btn" @click="clear()">Clear</button>
        {% ui.BindingSearch :result=search_result / %}
    </div>
    """
