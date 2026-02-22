import pytest
from django.test import RequestFactory
from tetra import Library
from tetra.router import Component, Router, route, path, re_path, include
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
class ClassRouter(Router):
    routes = {
        "/": Home,
        "/about/": About,
    }


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


def test_legacy_dict_router_params():
    """Test that legacy dict-based router can extract regex parameters."""
    request = _get_request("/re/999/")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "About" in html
    assert router.url_params == {"id": "999"}


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
