# Test that the nested counter component from the demo works correctly
import pytest
from playwright.sync_api import Page

from tetra import Library, Component, public

ui = Library("ui", "main")


@ui.register
class Counter(Component):
    count = public(0)
    current_sum = public(0)

    def load(self, current_sum=None, *args, **kwargs):
        if current_sum is not None:
            self.current_sum = current_sum

    @public
    def increment(self):
        self.count += 1

    @public
    def decrement(self):
        self.count -= 1

    def sum(self):
        return self.count + self.current_sum

    # language=html
    template = """
    <div class="counter-wrapper">
      <div class="border rounded p-3" style="border: 1px solid black; padding: 10px; margin: 10px;">
        <p class="counter-own-content" data-counter-key="{{ key }}">
          Count: <b class="count-value">{{ count }}</b>,
          Sum: <b class="sum-value">{{ sum }}</b>
          <button class="btn-decrement" @click="decrement()">Decrement</button>
          <button class="btn-increment" @click="increment()">Increment</button>
        </p>
        <div class="counter-children">
          {% slot default %}{% endslot %}
        </div>
      </div>
    </div>
    """


@ui.register
class NestedCounterWrapper(Component):
    # language=html
    template = """
    <div>
      {% load tetra %}
      {% ui.Counter key="counter-1" %}
        {% ui.Counter key="counter-2" current_sum=sum %}
          {% ui.Counter key="counter-3" current_sum=sum / %}
        {% /ui.Counter %}
      {% /ui.Counter %}
    </div>
    """


@ui.register
class NestedCounterWrapper2(Component):
    # language=html
    template = """
    <div>
      {% load tetra %}
      {% ui.Counter key="counter-a" %}
        {% ui.Counter key="counter-b" current_sum=sum %}
          {% ui.Counter key="counter-c" current_sum=sum / %}
        {% /ui.Counter %}
      {% /ui.Counter %}
    </div>
    """


@pytest.mark.playwright
def test_nested_counter_components(component_locator):
    """
    Test that nested Counter components work independently with proper state management.
    Each counter should maintain its own count and properly calculate sums based on parent counts.

    Structure:
    - Counter 1 (key="counter-1"): root counter, sum = count
    - Counter 2 (key="counter-2"): child of Counter 1, sum = count + parent.sum
    - Counter 3 (key="counter-3"): child of Counter 2, sum = count + parent.sum
    """
    component = component_locator(NestedCounterWrapper)

    # Get all three counters by their keys using the data-counter-key attribute
    counter1_content = component.locator('[data-counter-key="counter-1"]')
    counter2_content = component.locator('[data-counter-key="counter-2"]')
    counter3_content = component.locator('[data-counter-key="counter-3"]')

    # Verify initial state
    # Counter 1: count=0, sum=0
    assert counter1_content.locator(".count-value").text_content() == "0"
    assert counter1_content.locator(".sum-value").text_content() == "0"

    # Counter 2: count=0, current_sum=0 (from counter1.sum), sum=0
    assert counter2_content.locator(".count-value").text_content() == "0"
    assert counter2_content.locator(".sum-value").text_content() == "0"

    # Counter 3: count=0, current_sum=0 (from counter2.sum), sum=0
    assert counter3_content.locator(".count-value").text_content() == "0"
    assert counter3_content.locator(".sum-value").text_content() == "0"

    # Test Counter 1: Increment twice
    counter1_content.locator(".btn-increment").click()
    # Wait for the text to change from "0" to "1"
    counter1_content.locator('.count-value:has-text("1")').wait_for(
        state="visible", timeout=2000
    )
    assert counter1_content.locator(".count-value").text_content() == "1"
    assert counter1_content.locator(".sum-value").text_content() == "1"

    counter1_content.locator(".btn-increment").click()
    # Wait for the text to change from "1" to "2"
    counter1_content.locator('.count-value:has-text("2")').wait_for(
        state="visible", timeout=2000
    )
    assert counter1_content.locator(".count-value").text_content() == "2"
    assert counter1_content.locator(".sum-value").text_content() == "2"

    # Test Counter 2: Increment once
    counter2_content.locator(".btn-increment").click()
    counter2_content.locator('.count-value:has-text("1")').wait_for(
        state="visible", timeout=2000
    )
    assert counter2_content.locator(".count-value").text_content() == "1"

    # Test Counter 3: Increment once
    counter3_content.locator(".btn-increment").click()
    counter3_content.locator('.count-value:has-text("1")').wait_for(
        state="visible", timeout=2000
    )
    assert counter3_content.locator(".count-value").text_content() == "1"

    # Test decrement on Counter 1
    counter1_content.locator(".btn-decrement").click()
    counter1_content.locator('.count-value:has-text("1")').wait_for(
        state="visible", timeout=2000
    )
    assert counter1_content.locator(".count-value").text_content() == "1"
    assert counter1_content.locator(".sum-value").text_content() == "1"

    # Test decrement on Counter 2
    counter2_content.locator(".btn-decrement").click()
    counter2_content.locator('.count-value:has-text("0")').wait_for(
        state="visible", timeout=2000
    )
    assert counter2_content.locator(".count-value").text_content() == "0"

    # Test decrement on Counter 3
    counter3_content.locator(".btn-decrement").click()
    counter3_content.locator('.count-value:has-text("0")').wait_for(
        state="visible", timeout=2000
    )
    assert counter3_content.locator(".count-value").text_content() == "0"


@pytest.mark.playwright
def test_nested_counter_independence(component_locator):
    """
    Test that each nested counter maintains independent state.
    Clicking increment/decrement on one counter should not affect the count of other counters.
    """
    component = component_locator(NestedCounterWrapper2)

    counter_a_content = component.locator('[data-counter-key="counter-a"]')
    counter_b_content = component.locator('[data-counter-key="counter-b"]')
    counter_c_content = component.locator('[data-counter-key="counter-c"]')

    # Increment counter-a 3 times
    for i in range(3):
        counter_a_content.locator(".btn-increment").click()
        counter_a_content.locator(f'.count-value:has-text("{i+1}")').wait_for(
            state="visible", timeout=2000
        )

    # Verify counter-a is at 3
    assert counter_a_content.locator(".count-value").text_content() == "3"

    # Verify counter-b and counter-c are still at 0
    assert counter_b_content.locator(".count-value").text_content() == "0"
    assert counter_c_content.locator(".count-value").text_content() == "0"

    # Increment counter-c 5 times
    for i in range(5):
        counter_c_content.locator(".btn-increment").click()
        counter_c_content.locator(f'.count-value:has-text("{i+1}")').wait_for(
            state="visible", timeout=2000
        )

    # Verify counter-c is at 5
    assert counter_c_content.locator(".count-value").text_content() == "5"

    # Verify counter-a is still at 3 and counter-b is still at 0
    assert counter_a_content.locator(".count-value").text_content() == "3"
    assert counter_b_content.locator(".count-value").text_content() == "0"

    # Decrement counter-b twice
    counter_b_content.locator(".btn-decrement").click()
    counter_b_content.locator('.count-value:has-text("-1")').wait_for(
        state="visible", timeout=2000
    )
    counter_b_content.locator(".btn-decrement").click()
    counter_b_content.locator('.count-value:has-text("-2")').wait_for(
        state="visible", timeout=2000
    )

    # Verify counter-b is at -2
    assert counter_b_content.locator(".count-value").text_content() == "-2"

    # Verify others are unchanged
    assert counter_a_content.locator(".count-value").text_content() == "3"
    assert counter_c_content.locator(".count-value").text_content() == "5"
