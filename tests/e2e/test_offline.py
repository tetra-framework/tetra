import pytest
from playwright.sync_api import Page, expect
from tetra import Library, Component

ui = Library("ui", "main")


@ui.register
class OfflineTestComponent(Component):
    # language=html
    template = """
    <div id="status-component" tetra-reactive tetra-subscription="broadcast">
        <div id="online-status" x-text="$store.tetraStatus.online ? 'online' : 'offline'"></div>
        <div id="disconnected-event">no event</div>
        <script>
            document.addEventListener('tetra:websocket-disconnected', () => {
                document.getElementById('disconnected-event').innerText = 'disconnected event fired';
            });
        </script>
    </div>
    """


@pytest.mark.playwright
def test_offline_event_dispatched(page: Page, component_locator):
    # Set short timeouts for testing
    page.add_init_script(
        """
        window.__tetra_useWebsockets = true;
        window.__tetra_onlineTimeout = 500;
        window.__tetra_pingTimeout = 100;
    """
    )

    component = component_locator(OfflineTestComponent)

    # Initially should be online
    status_div = component.locator("#online-status")

    # Force online status if WebSocket is not available
    page.evaluate(
        """
        if (Alpine.store('tetraStatus').online !== true) {
            Alpine.store('tetraStatus').online = true;
            if (Tetra.offlineTimeout) {
                clearTimeout(Tetra.offlineTimeout);
            }
            Tetra.offlineTimeout = setTimeout(() => Tetra.checkOnlineStatus(), window.__tetra_onlineTimeout || 10000);
        }
    """
    )
    expect(status_div).to_have_text("online", timeout=5000)

    # We need to simulate the server NOT responding to ping.
    # In a real playwright test with the tetra test server,
    # the server WILL respond to ping.

    # One way to simulate "offline" is to close the websocket connection.
    # initially we might not have WS, but we can force it
    page.evaluate(
        """
        if (Tetra.ws) {
            Tetra.ws.close();
        } else {
            Tetra.setOfflineStatus();
        }
    """
    )

    # Wait for the event to fire
    event_div = component.locator("#disconnected-event")

    expect(event_div).to_have_text("disconnected event fired", timeout=3000)

    # Wait for the onlineTimeout (1000ms) + pingTimeout (500ms)
    # page.wait_for_timeout(2000)

    expect(status_div).to_have_text("offline", timeout=5000)
