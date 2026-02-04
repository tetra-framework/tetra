import pytest
from django.test import RequestFactory
from tetra import Library
from tetra.router import Component, Router
from tetra.middleware import TetraDetails
from tetra.tests.fixtures import add_session_to_request


library = Library("test_router", "tetra")


@library.register
class Home(Component):
    template = "<div>Home</div>"


@library.register
class About(Component):
    template = "<div>About</div>"


@library.register
class ClassRouter(Router):
    routes = {
        "/": Home,
        "/about/": About,
        "/re/(?P<id>\\d+)/": About,
        "/re-str/(?P<id>\\d+)/": "test_router.About",
        "/string-route/": "test_router.Home",
    }


def _get_request(path):
    factory = RequestFactory()
    request = factory.get(path)
    add_session_to_request(request)
    request.tetra = TetraDetails(request)
    request.tetra.set_url(request.build_absolute_uri())
    return request


def test_router_initial_render_home():
    """Test that the router renders the Home component for the root path."""
    request = _get_request("/")
    router = ClassRouter(request)
    html = router.render()
    assert "Home" in html
    assert router.current_component == "test_router.Home"


def test_router_initial_render_about():
    """Test that the router renders the About component for the /about/ path."""
    request = _get_request("/about/")
    router = ClassRouter(request)
    html = router.render()
    assert "About" in html
    assert router.current_component == "test_router.About"


def test_router_navigate():
    """Test programmatic navigation between routes within the router."""
    request = _get_request("/")
    router = ClassRouter(request)
    router.navigate("/about/", push=False)
    html = router.render()
    assert "About" in html
    assert router.current_component == "test_router.About"


def test_class_router_regex_match():
    """Test that routes with regex parameters match correctly."""
    request = _get_request("/re/123/")
    router = ClassRouter(request)
    html = router.render()
    assert "About" in html
    assert router.current_component == "test_router.About"


def test_class_router_regex_match_str():
    """Test regex route matching when the component is specified as a string path."""
    request = _get_request("/re-str/123/")
    router = ClassRouter(request)
    html = router.render()
    assert "About" in html
    assert router.current_component == "test_router.About"


def test_class_router_string_route():
    """Test matching a simple string route to its registered component."""
    request = _get_request("/string-route/")
    router = ClassRouter(request)
    html = router.render()
    assert "Home" in html
    assert router.current_component == "test_router.Home"


def test_router_no_match():
    """Test that the router handles non-existent paths by not matching any component."""
    request = _get_request("/non-existent/")
    router = ClassRouter(request)
    html = router.render()
    assert "Home" not in html
    assert "About" not in html
    assert router.current_component == ""


def test_link_render():
    """Test rendering the Link component and verify it generates the correct href and label."""
    from tetra import Library
    from tetra.router import Link

    # Ensure Link is registered (it might have been lost due to module reloads)
    if not getattr(Link, "_library", None):
        default_lib = Library("default", "tetra")
        default_lib.register(Link)

    request = _get_request("/")
    link = Link(request, to="/about/", label="Go to About")
    html = link.render()
    assert 'href="/about/"' in html
    assert "Go to About" in html
