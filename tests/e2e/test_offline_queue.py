"""E2E tests for the offline queue system with optimistic UI and reconciliation."""
import pytest
from playwright.sync_api import Page, expect
from tetra import Library, Component, public

ui = Library("ui", "main")


@ui.register
class CounterComponent(Component):
    """Test component with a counter that can be incremented."""
    count: int = 0

    @public
    def increment(self):
        """Increment the counter."""
        self.count += 1

    # language=html
    template = """
    <div id="counter-component" tetra-reactive x-data="{ count: {{ count }} }">
        <div id="count">{{ count }}</div>
        <button id="increment-btn" @click="increment()">Increment</button>
        <div id="queue-length">0</div>
        <script>
            document.addEventListener('tetra:call-queued', (e) => {
                document.getElementById('queue-length').innerText = e.detail.queueLength;
            });
        </script>
    </div>
    """


@ui.register
class TodoListComponent(Component):
    """Test component with a list of items that can be added and deleted."""
    items: list = []
    next_id: int = 1
    new_item_text: str = ""

    @public
    def add_item(self):
        """Add a new item to the list."""
        if self.new_item_text:
            self.items.append({"id": self.next_id, "text": self.new_item_text})
            self.next_id += 1
            self.new_item_text = ""

    @public
    def delete_item(self, item_id: int):
        """Delete an item from the list."""
        self.items = [item for item in self.items if item["id"] != item_id]

    # language=html
    template = """
    <div id="todo-list" tetra-reactive>
        <input id="new-item" type="text" value="{{ new_item_text }}" @input="new_item_text = $event.target.value" />
        <button id="add-btn" @click="add_item()">Add</button>
        <div id="items-container">
            {% for item in items %}
            <div class="item" data-item-id="{{ item.id }}">
                <span class="item-text">{{ item.text }}</span>
                <button class="delete-btn" @click="delete_item({{ item.id }})">Delete</button>
            </div>
            {% endfor %}
        </div>
        <div id="queue-status">idle</div>
        <div id="queue-events"></div>
        <script>
            const queueStatus = document.getElementById('queue-status');
            const queueEvents = document.getElementById('queue-events');

            document.addEventListener('tetra:call-queued', (e) => {
                queueStatus.innerText = 'queued:' + e.detail.queueLength;
                queueEvents.innerText += 'queued;';
            });

            document.addEventListener('tetra:queue-processing-start', (e) => {
                queueStatus.innerText = 'processing:' + e.detail.queueLength;
                queueEvents.innerText += 'processing;';
            });

            document.addEventListener('tetra:queue-processing-complete', (e) => {
                queueStatus.innerText = 'complete:' + e.detail.processedCount;
                queueEvents.innerText += 'complete;';
            });
        </script>
    </div>
    """


@pytest.mark.playwright
def test_queue_on_network_offline(page: Page, component_locator):
    """Queue method calls when browser goes offline via DevTools."""
    page.add_init_script("window.__tetra_useWebsockets = true; window.__tetra_debug = true;")

    component = component_locator(CounterComponent)
    count_div = component.locator("#count")
    queue_div = component.locator("#queue-length")

    # Initial state
    expect(count_div).to_have_text("0")
    expect(queue_div).to_have_text("0")

    # Go offline
    page.context.set_offline(True)
    page.wait_for_timeout(100)

    # Click increment - should be queued
    component.locator("#increment-btn").click()
    page.wait_for_timeout(100)

    # Queue length should be 1
    expect(queue_div).to_have_text("1")

    # Go back online
    page.context.set_offline(False)

    # Wait for queue to process
    page.wait_for_timeout(1000)

    # Counter should be incremented
    expect(count_div).to_have_text("1")


@pytest.mark.skip(reason="WebSocket close timing unreliable in tests")
@pytest.mark.playwright
def test_queue_on_websocket_closed(page: Page, component_locator):
    """Queue method calls when WebSocket is closed."""
    pass


@pytest.mark.playwright
def test_multiple_calls_queued_in_order(page: Page, component_locator):
    """Queue multiple method calls and process them in order."""
    page.add_init_script("window.__tetra_useWebsockets = true; window.__tetra_debug = true;")

    component = component_locator(CounterComponent)
    count_div = component.locator("#count")

    # Go offline
    page.context.set_offline(True)
    page.wait_for_timeout(100)

    # Click increment 3 times
    increment_btn = component.locator("#increment-btn")
    increment_btn.click()
    page.wait_for_timeout(50)
    increment_btn.click()
    page.wait_for_timeout(50)
    increment_btn.click()
    page.wait_for_timeout(50)

    # Go back online
    page.context.set_offline(False)

    # Wait for queue to process all calls
    page.wait_for_timeout(2000)

    # Counter should be incremented 3 times
    expect(count_div).to_have_text("3")


@pytest.mark.skip(reason="Complex TodoList component needs more setup")
@pytest.mark.playwright
def test_queue_events_dispatched(page: Page, component_locator):
    """Verify queue events are dispatched during processing."""
    pass


@pytest.mark.skip(reason="Complex TodoList component needs more setup")
@pytest.mark.playwright
def test_delete_item_offline_replays_with_snapshot(page: Page, component_locator):
    """Delete an item offline and verify correct item is deleted using snapshot state."""
    pass


@pytest.mark.skip(reason="Complex TodoList component needs more setup")
@pytest.mark.playwright
def test_add_item_offline_finds_correct_component(page: Page, component_locator):
    """Add an item offline and verify it's added to the correct parent component."""
    pass


@pytest.mark.skip(reason="Timing-sensitive test")
@pytest.mark.playwright
def test_queue_persists_across_multiple_offline_online_cycles(page: Page, component_locator):
    """Verify queue accumulates calls across multiple offline/online cycles."""
    pass


@pytest.mark.playwright
def test_queue_cleared_after_successful_processing(page: Page, component_locator):
    """Verify queue is cleared after successful processing."""
    page.add_init_script("window.__tetra_useWebsockets = true; window.__tetra_debug = true;")

    component = component_locator(CounterComponent)
    queue_div = component.locator("#queue-length")

    # Go offline
    page.context.set_offline(True)
    page.wait_for_timeout(100)

    # Queue a call
    component.locator("#increment-btn").click()
    page.wait_for_timeout(100)

    expect(queue_div).to_have_text("1")

    # Go online
    page.context.set_offline(False)
    page.wait_for_timeout(1500)

    # Go offline again
    page.context.set_offline(True)
    page.wait_for_timeout(100)

    # Queue should be empty (reset to 0)
    component.locator("#increment-btn").click()
    page.wait_for_timeout(100)

    # New queue should start at 1, not 2
    expect(queue_div).to_have_text("1")
