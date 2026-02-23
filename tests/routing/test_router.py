import pytest
from django.test import RequestFactory
from tetra import Library
from tetra.router import (
    Component,
    Router,
    route,
    path,
    re_path,
    include,
    reverse,
    reverse_lazy,
    _route_registry,
)
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
class PatientView(Component):
    patient_id: int = 0

    template = "<div>Patient {{ patient_id }}</div>"

    def load(self, *args, **kwargs):
        # Explicitly get route parameter from request.tetra (secure)
        patient_id = self.request.tetra.route_params.get("patient_id")
        if patient_id:
            self.patient_id = int(patient_id)


@library.register
class BloodPressure(Component):
    patient_id: int = 0

    template = "<div>BP for patient {{ patient_id }}</div>"

    def load(self, *args, **kwargs):
        # Explicitly get route parameter from request.tetra (secure)
        patient_id = self.request.tetra.route_params.get("patient_id")
        if patient_id:
            self.patient_id = int(patient_id)


@library.register
class Sugar(Component):
    patient_id: int = 0

    template = "<div>Sugar for patient {{ patient_id }}</div>"

    def load(self, *args, **kwargs):
        # Explicitly get route parameter from request.tetra (secure)
        patient_id = self.request.tetra.route_params.get("patient_id")
        if patient_id:
            self.patient_id = int(patient_id)


@library.register
class RouteBasedRouter(Router):
    """Router using new Route-based routing."""

    routes = [
        route("", Home),
        route("about/", About),
        route("/re/(?P<id>\\d+)/", About),
        route("/re-str/(?P<id>\\d+)/", "test_router.About"),
        route("/string-route/", "test_router.Home"),
    ]


@library.register
class RouteWithParamsRouter(Router):
    """Router with URL parameters."""

    routes = [
        route("", Home),
        route("patient/<int:patient_id>/", PatientView),
    ]


@library.register
class PatientRouter(Router):
    """Sub-router for patient-specific pages (delegation pattern)."""

    routes = [
        route("", PatientView),
        route("bp/", BloodPressure),
        route("sugar/", Sugar),
    ]


@library.register
class NestedRouter(Router):
    """Router with nested routes for patient sub-pages (explicit pattern)."""

    routes = [
        route("", Home),
        route(
            "patient/<int:patient_id>/",
            PatientView,
            children=[
                route("bp/", BloodPressure),
                route("sugar/", Sugar),
            ],
        ),
    ]


@library.register
class DelegatedRouter(Router):
    """Router that delegates to PatientRouter (delegation pattern)."""

    routes = [
        route("", Home),
        route("patient/<int:patient_id>/", PatientRouter, delegate=True),
    ]


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
    router = RouteBasedRouter(request)
    html = router.render()
    assert "Home" in html
    assert router.current_component == "test_router.Home"


def test_router_initial_render_about():
    """Test that the router renders the About component for the /about/ path."""
    request = _get_request("/about/")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "About" in html
    assert router.current_component == "test_router.About"


def test_router_navigate():
    """Test programmatic navigation between routes within the router."""
    request = _get_request("/")
    router = RouteBasedRouter(request)
    router.navigate("/about/", push=False)
    html = router.render()
    assert "About" in html
    assert router.current_component == "test_router.About"


def test_router_home():
    """Test Route-based router renders Home for root path."""
    request = _get_request("/")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "Home" in html
    assert router.current_component == "test_router.Home"


def test_router_about():
    """Test Route-based router renders About page."""
    request = _get_request("/about/")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "About" in html
    assert router.current_component == "test_router.About"


def test_router_regex_match():
    """Test that routes with regex parameters match correctly."""
    request = _get_request("/re/123/")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "About" in html
    assert router.current_component == "test_router.About"


def test_router_regex_match_str():
    """Test regex route matching when the component is specified as a string path."""
    request = _get_request("/re-str/123/")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "About" in html
    assert router.current_component == "test_router.About"


def test_router_string_route():
    """Test matching a simple string route to its registered component."""
    request = _get_request("/string-route/")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "Home" in html
    assert router.current_component == "test_router.Home"


def test_router_no_match():
    """Test that the router handles non-existent paths by not matching any component."""
    request = _get_request("/non-existent/")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "Home" not in html
    assert "About" not in html
    assert router.current_component == ""


def test_link_render():
    """Test rendering the Link component and verify it generates the correct href."""
    from tetra import Library
    from tetra.router import Link

    # Ensure Link is registered (it might have been lost due to module reloads)
    if not getattr(Link, "_library", None):
        default_lib = Library("default", "tetra")
        default_lib.register(Link)

    request = _get_request("/")
    link = Link(request, to="/about/")
    html = link.render()
    assert 'href="/about/"' in html
    assert "<a" in html


def test_link_default_to_param():
    """Test that Link defaults to='#' if not provided."""
    from tetra import Library
    from tetra.router import Link

    if not getattr(Link, "_library", None):
        default_lib = Library("default", "tetra")
        default_lib.register(Link)

    request = _get_request("/")
    link = Link(request)
    html = link.render()
    assert 'href="#"' in html


def test_link_custom_active_class():
    """Test Link with custom active_class parameter."""
    from tetra import Library
    from tetra.router import Link

    if not getattr(Link, "_library", None):
        default_lib = Library("default", "tetra")
        default_lib.register(Link)

    request = _get_request("/")
    link = Link(request, to="/about/", active_class="current")
    html = link.render()
    assert "'current'" in html  # active_class should be in Alpine.js binding


def test_link_active_class_binding():
    """Test that Link includes Alpine.js active class binding."""
    from tetra import Library
    from tetra.router import Link

    if not getattr(Link, "_library", None):
        default_lib = Library("default", "tetra")
        default_lib.register(Link)

    request = _get_request("/test/")
    link = Link(request, to="/test/")
    html = link.render()
    # Should have Alpine.js binding for active class
    assert ":class=" in html
    assert "'active'" in html
    assert "window.location.pathname" in html


def test_link_click_prevention():
    """Test that Link includes @click.prevent directive."""
    from tetra import Library
    from tetra.router import Link

    if not getattr(Link, "_library", None):
        default_lib = Library("default", "tetra")
        default_lib.register(Link)

    request = _get_request("/")
    link = Link(request, to="/about/")
    html = link.render()
    assert "@click.prevent=" in html or '@click.prevent="click()"' in html


def test_link_with_slot_content():
    """Test that Link accepts slot content syntax between {% Link %}...{% /Link %} tags."""
    from tetra.helpers import render_component_tag
    from bs4 import BeautifulSoup

    request = _get_request("/")

    # Render Link with content in default slot using template tag syntax
    # Link is registered in the tetra.default library
    html = render_component_tag(
        request,
        '{% Link to="/about/" %}Go to About{% /Link %}',
    )

    # Parse HTML and verify Link component renders correctly
    soup = BeautifulSoup(html, "html.parser")
    link_tag = soup.find("a")

    assert link_tag is not None, "Link <a> tag not found"
    assert (
        link_tag.get("href") == "/about/"
    ), f"Expected href='/about/', got {link_tag.get('href')}"

    # Verify the Link has the necessary attributes for Tetra components
    assert link_tag.get("tetra-component") == "tetra__default__link"
    assert link_tag.get("@click.prevent") is not None or "@click.prevent" in str(
        link_tag
    )
    assert "Go to About" in html


def test_link_with_kwargs():
    """Test Link with various URL paths including parameters."""
    from tetra import Library
    from tetra.router import Link

    if not getattr(Link, "_library", None):
        default_lib = Library("default", "tetra")
        default_lib.register(Link)

    request = _get_request("/")

    # Test with parameterized URL
    link = Link(request, to="/patient/123/")
    html = link.render()
    assert 'href="/patient/123/"' in html

    # Test with query string
    link = Link(request, to="/search/?q=test")
    html = link.render()
    assert 'href="/search/?q=test"' in html


def test_route_with_params():
    """Test Route-based router extracts URL parameters."""
    request = _get_request("/patient/123/")
    router = RouteWithParamsRouter(request)
    html = router.render()
    assert "Patient 123" in html
    assert router.current_component == "test_router.PatientView"
    assert router.url_params == {"patient_id": 123}


def test_nested_route_parent_only():
    """Test nested router matches parent route."""
    request = _get_request("/patient/456/")
    router = NestedRouter(request)
    html = router.render()
    assert "Patient 456" in html
    assert router.current_component == "test_router.PatientView"
    assert router.url_params == {"patient_id": 456}


def test_nested_route_child_bp():
    """Test nested router matches blood pressure child route."""
    request = _get_request("/patient/789/bp/")
    router = NestedRouter(request)
    html = router.render()
    assert "BP for patient 789" in html
    assert router.current_component == "test_router.BloodPressure"
    # URL params from prefix matching are strings
    assert router.url_params == {"patient_id": "789"}


def test_nested_route_child_sugar():
    """Test nested router matches sugar child route."""
    request = _get_request("/patient/321/sugar/")
    router = NestedRouter(request)
    html = router.render()
    assert "Sugar for patient 321" in html
    assert router.current_component == "test_router.Sugar"
    # URL params from prefix matching are strings
    assert router.url_params == {"patient_id": "321"}


def test_nested_route_navigation():
    """Test navigation between nested routes."""
    request = _get_request("/")
    router = NestedRouter(request)

    # Start at home
    assert router.current_component == "test_router.Home"

    # Navigate to patient
    router.navigate("/patient/100/", push=False)
    assert router.current_component == "test_router.PatientView"
    # Django converts <int:patient_id> to int for exact matches
    assert router.url_params["patient_id"] == 100

    # Navigate to BP - prefix matching returns strings
    router.navigate("/patient/100/bp/", push=False)
    assert router.current_component == "test_router.BloodPressure"
    assert router.url_params["patient_id"] == "100"

    # Navigate to Sugar - prefix matching returns strings
    router.navigate("/patient/100/sugar/", push=False)
    assert router.current_component == "test_router.Sugar"
    assert router.url_params["patient_id"] == "100"


# ===== Delegated routing tests =====


def test_delegated_router_parent():
    """Test delegated router matches parent PatientRouter with remaining path."""
    request = _get_request("/patient/500/")
    router = DelegatedRouter(request)
    html = router.render()
    # Should render PatientRouter, which in turn renders PatientView
    assert "Patient 500" in html or "PatientRouter" in html
    assert router.current_component == "test_router.PatientRouter"
    assert router.url_params == {"patient_id": 500}


def test_delegated_router_child_bp():
    """Test delegated router with bp sub-route."""
    request = _get_request("/patient/600/bp/")
    router = DelegatedRouter(request)
    html = router.render()
    # PatientRouter should handle the /bp/ part internally
    assert router.current_component == "test_router.PatientRouter"
    # URL params from prefix matching are strings
    assert router.url_params == {"patient_id": "600"}


# ===== Router.reverse() tests =====


@library.register
class NamedRoutesRouter(Router):
    """Router with named routes for testing reverse()."""

    routes = [
        route("", Home, name="home"),
        route("about/", About, name="about"),
        route("patient/<int:patient_id>/", PatientView, name="patient-detail"),
        route(
            "patient/<int:patient_id>/",
            PatientView,
            name="patient-root",
            children=[
                route("bp/", BloodPressure, name="patient-bp"),
                route("sugar/", Sugar, name="patient-sugar"),
            ],
        ),
    ]


def test_reverse_simple_route():
    """Test reversing a simple named route without parameters."""
    url = NamedRoutesRouter.reverse("home")
    assert url == ""


def test_reverse_simple_route_with_path():
    """Test reversing a simple named route with a path."""
    url = NamedRoutesRouter.reverse("about")
    assert url == "about/"


def test_reverse_route_with_params():
    """Test reversing a route with URL parameters."""
    url = NamedRoutesRouter.reverse("patient-detail", patient_id=123)
    assert url == "patient/123/"


def test_reverse_nonexistent_route():
    """Test that reversing a nonexistent route raises ValueError."""
    with pytest.raises(ValueError, match="Route 'nonexistent' not found"):
        NamedRoutesRouter.reverse("nonexistent")


def test_reverse_nested_child_route():
    """Test reversing a nested child route."""
    url = NamedRoutesRouter.reverse("patient-bp", patient_id=456)
    # Should combine parent and child paths
    assert "patient" in url and "bp" in url


def test_reverse_lazy():
    """Test that reverse_lazy returns a lazy object that evaluates correctly."""
    lazy_url = NamedRoutesRouter.reverse_lazy("about")
    # Lazy object should convert to string when needed
    assert str(lazy_url) == "about/"


def test_reverse_lazy_with_params():
    """Test reverse_lazy with URL parameters."""
    lazy_url = NamedRoutesRouter.reverse_lazy("patient-detail", patient_id=789)
    assert str(lazy_url) == "patient/789/"


# ===== Global route reversal tests =====


@library.register
class UserRouter(Router):
    """Router with namespace for testing global reversal."""

    namespace = "user"

    routes = [
        route("", Home, name="home"),
        route("profile/<int:user_id>/", PatientView, name="profile"),
    ]


@library.register
class AdminRouter(Router):
    """Another router with namespace for testing global reversal."""

    namespace = "admin"

    routes = [
        route("", Home, name="dashboard"),
        route("users/", About, name="users"),
    ]


@library.register
class NoNamespaceRouter(Router):
    """Router without namespace for testing global reversal."""

    routes = [
        route("", Home, name="global-home"),
        route("contact/", About, name="contact"),
    ]


def test_global_reverse_with_namespace():
    """Test global reverse() with namespaced routes."""
    url = reverse("user:profile", user_id=123)
    assert url == "profile/123/"


def test_global_reverse_without_namespace():
    """Test global reverse() without namespace."""
    url = reverse("global-home")
    assert url == ""


def test_global_reverse_contact():
    """Test global reverse() for contact route."""
    url = reverse("contact")
    assert url == "contact/"


def test_global_reverse_admin_namespace():
    """Test global reverse() with admin namespace."""
    url = reverse("admin:users")
    assert url == "users/"


def test_global_reverse_nonexistent():
    """Test that global reverse() raises ValueError for nonexistent route."""
    with pytest.raises(ValueError, match="Route 'nonexistent:route' not found"):
        reverse("nonexistent:route")


def test_global_reverse_lazy_with_namespace():
    """Test global reverse_lazy() with namespace."""
    lazy_url = reverse_lazy("user:home")
    assert str(lazy_url) == ""


def test_global_reverse_lazy_with_params():
    """Test global reverse_lazy() with parameters."""
    lazy_url = reverse_lazy("user:profile", user_id=456)
    assert str(lazy_url) == "profile/456/"
