import pytest
from playwright.sync_api import Page
from tetra import Library, Component, public
from django.http import HttpResponse

lib = Library("redirect_test", "main")


@lib.register
class RedirectComponent(Component):
    @public
    def do_redirect(self):
        self.client._redirect("/target")

    template = """
    <div>
        <button id="redirect-btn" @click="do_redirect()">Redirect Me</button>
    </div>
    """


def target_view(request):
    return HttpResponse("Target Page")


@pytest.mark.playwright
def test_redirect(page: Page, component_locator, live_server):
    """Verify that calling self.client._redirect() on the server triggers a client-side navigation."""
    # We can't easily add a new URL to live_server mid-test,
    # but we can redirect to a URL that we know exists or just
    # check if the browser tried to navigate there.

    component = component_locator(RedirectComponent)

    # Click the button and wait for navigation (it might 404, but that's okay,
    # it proves the redirect happened)
    component.locator("#redirect-btn").click()

    page.wait_for_url("**/target")

    assert "/target" in page.url
