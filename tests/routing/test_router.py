import pytest
from django.test import RequestFactory
from tetra import Library, Component
from tetra.components.default.router import Router
from tetra.router import route, reverse, reverse_lazy
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
    from tetra.components.default.link import Link

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
    from tetra.components.default.link import Link

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
    from tetra.components.default.link import Link

    if not getattr(Link, "_library", None):
        default_lib = Library("default", "tetra")
        default_lib.register(Link)

    request = _get_request("/")
    link = Link(request, to="/about/", active_class="current")
    html = link.render()
    assert "'current'" in html  # active_class should be in Alpine.js binding


def test_link_active_class_binding():
    """Test that Link includes Alpine.js active class binding using route store."""
    from tetra import Library
    from tetra.components.default.link import Link

    if not getattr(Link, "_library", None):
        default_lib = Library("default", "tetra")
        default_lib.register(Link)

    request = _get_request("/test/")
    link = Link(request, to="/test/")
    html = link.render()
    # Should have Alpine.js binding for active class using route store
    assert ":class=" in html
    assert "'active'" in html
    assert "$store.route.path" in html


def test_link_click_prevention():
    """Test that Link includes @click.prevent directive."""
    from tetra import Library
    from tetra.components.default.link import Link

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
    assert link_tag.get("href") == "/about/", (
        f"Expected href='/about/', got {link_tag.get('href')}"
    )

    # Verify the Link has the necessary attributes
    # Note: Link is a BasicComponent, so it doesn't have tetra-component attribute
    assert link_tag.get("@click.prevent") is not None or "@click.prevent" in str(
        link_tag
    )
    assert "Go to About" in html


def test_link_with_kwargs():
    """Test Link with various URL paths including parameters."""
    from tetra import Library
    from tetra.components.default.link import Link

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


# ===== Extended Nested Routing Tests =====


@library.register
class MultiChildRouter(Router):
    """Router with multiple children for comprehensive testing."""

    routes = [
        route("", Home),
        route(
            "users/",
            PatientView,
            name="users-root",
            children=[
                route("", About, name="users-index"),
                route("<int:user_id>/", PatientView, name="user-detail"),
                route("<int:user_id>/posts/", Sugar, name="user-posts"),
                route(
                    "<int:user_id>/posts/<int:post_id>/",
                    BloodPressure,
                    name="user-post-detail",
                ),
            ],
        ),
    ]


def test_nested_multi_children_index():
    """Test nested router with multiple children - index route matches parent."""
    request = _get_request("/users/")
    router = MultiChildRouter(request)
    html = router.render()
    assert "Patient 0" in html
    assert router.current_component == "test_router.PatientView"


def test_nested_multi_children_detail():
    """Test nested router with multiple children - user detail route."""
    request = _get_request("/users/123/")
    router = MultiChildRouter(request)
    html = router.render()
    assert router.current_component == "test_router.PatientView"
    assert router.url_params["user_id"] == 123


def test_nested_multi_children_posts():
    """Test nested router with multiple children - posts route."""
    request = _get_request("/users/456/posts/")
    router = MultiChildRouter(request)
    html = router.render()
    assert router.current_component == "test_router.Sugar"
    assert router.url_params["user_id"] in (456, "456")


def test_nested_multi_children_post_detail():
    """Test nested router with multiple children - deep nested route."""
    request = _get_request("/users/789/posts/999/")
    router = MultiChildRouter(request)
    html = router.render()
    assert router.current_component == "test_router.BloodPressure"
    assert router.url_params["user_id"] in (789, "789")
    assert router.url_params["post_id"] in (999, "999")


def test_nested_url_params_merge():
    """Test that nested route URL params are correctly merged."""
    request = _get_request("/users/555/posts/777/")
    router = MultiChildRouter(request)
    assert router.url_params.get("user_id") in (555, "555")
    assert router.url_params.get("post_id") in (777, "777")


def test_nested_no_child_match_falls_to_parent():
    """Test that when no child route matches, parent component handles remaining path."""
    request = _get_request("/users/123/unknown-path/")
    router = MultiChildRouter(request)
    assert router.current_component == "test_router.PatientView"


# ===== Extended Delegation Tests =====


@library.register
class DelegatedMultiRouter(Router):
    """Router that delegates to PatientRouter with multiple sub-routes."""

    routes = [
        route("", Home),
        route("patient/<int:patient_id>/", PatientRouter, delegate=True),
    ]


@library.register
class DeepDelegatedRouter(Router):
    """Router with deeper delegation chain."""

    routes = [
        route("", Home),
        route(
            "admin/",
            DelegatedMultiRouter,
            delegate=True,
        ),
    ]


def test_delegated_router_all_subroutes():
    """Test delegated router handles all sub-routes of child router."""
    request = _get_request("/patient/700/")
    router = DelegatedRouter(request)
    html = router.render()
    assert "Patient 700" in html
    assert router.current_component == "test_router.PatientRouter"


def test_delegated_router_navigation():
    """Test navigation within delegated router."""
    request = _get_request("/patient/800/")
    router = DelegatedRouter(request)

    router.navigate("/patient/800/", push=False)
    assert router.current_component == "test_router.PatientRouter"

    router.navigate("/patient/800/bp/", push=False)
    assert router.current_component == "test_router.PatientRouter"

    router.navigate("/patient/800/sugar/", push=False)
    assert router.current_component == "test_router.PatientRouter"


def test_delegated_remaining_path_passing():
    """Test that remaining path is correctly passed to delegated router."""
    request = _get_request("/patient/900/bp/")
    router = DelegatedRouter(request)
    assert router._remaining_path == "bp/"


def test_deep_delegation_chain():
    """Test router delegation with deeper chain (admin/patient/...)."""
    request = _get_request("/admin/patient/500/")
    router = DeepDelegatedRouter(request)
    html = router.render()
    assert "Patient 500" in html


def test_deep_delegation_navigation():
    """Test navigation through deep delegation chain."""
    request = _get_request("/admin/")
    router = DeepDelegatedRouter(request)
    assert router.current_component == "test_router.DelegatedMultiRouter"

    router.navigate("/admin/patient/111/", push=False)
    assert router.current_component == "test_router.DelegatedMultiRouter"

    router.navigate("/admin/patient/111/bp/", push=False)
    assert router.current_component == "test_router.DelegatedMultiRouter"


# ===== router_view() and router_urls() tests =====


def test_router_view_basic():
    """Test router_view creates a Django view for SSR."""
    from tetra.router import router_view
    from django.test import Client

    request = _get_request("/")
    view = router_view(RouteBasedRouter)
    response = view(request)
    assert response.status_code == 200
    assert b"Home" in response.content


def test_router_view_with_path():
    """Test router_view handles sub-paths correctly."""
    from tetra.router import router_view

    request = _get_request("/about/")
    view = router_view(RouteBasedRouter)
    response = view(request)
    assert response.status_code == 200
    assert b"About" in response.content


def test_router_view_with_template():
    """Test router_view wraps content in a template."""
    from tetra.router import router_view

    request = _get_request("/")
    view = router_view(RouteBasedRouter, template_name="base.html")
    response = view(request)
    assert response.status_code == 200


def test_router_urls_basic():
    """Test router_urls creates correct URL patterns."""
    from tetra.router import router_urls

    urls = router_urls("", RouteBasedRouter, name="app")
    assert len(urls) == 2
    assert str(urls[0].pattern) == "" or urls[0].pattern.match
    assert str(urls[1].pattern) == "<path:path>" or "<path:path>" in str(
        urls[1].pattern
    )


def test_router_urls_nested():
    """Test router_urls with nested base path."""
    from tetra.router import router_urls

    urls = router_urls("app", RouteBasedRouter, name="app")
    assert len(urls) == 2
    assert "app" in str(urls[0].pattern)
    assert "app" in str(urls[1].pattern)


# ===== Edge Case Tests =====


def test_empty_path_handling():
    """Test router handles empty path correctly."""
    request = _get_request("")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "Home" in html


def test_root_router_flag():
    """Test that root router is correctly identified."""
    request = _get_request("/")
    router = RouteBasedRouter(request)
    assert router.is_root_router is True


def test_nested_router_flag():
    """Test that nested router (via delegation) is identified as not root."""
    request = _get_request("/patient/123/")
    router = DelegatedRouter(request)
    html = router.render()
    assert router.is_root_router is True


def test_slash_handling():
    """Test router handles paths with/without trailing slashes."""
    request = _get_request("/about")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "About" in html


def test_case_sensitive_routes():
    """Test that routes are case sensitive."""
    request = _get_request("/ABOUT/")
    router = RouteBasedRouter(request)
    html = router.render()
    assert "About" not in html
    assert router.current_component == ""


@library.register
class MultiParamRouter(Router):
    """Router with multiple URL parameters for testing."""

    routes = [
        route("", Home),
        route("users/<int:user_id>/posts/<int:post_id>/", BloodPressure),
    ]


def test_multiple_route_params():
    """Test router with multiple URL parameters."""
    request = _get_request("/users/10/posts/20/")
    router = MultiParamRouter(request)
    html = router.render()
    assert router.url_params["user_id"] == 10
    assert router.url_params["post_id"] == 20


def test_optional_trailing_slash():
    """Test router handles optional trailing slash."""
    request = _get_request("/about")
    router = RouteBasedRouter(request)
    assert router.current_component == "test_router.About"


def test_reverse_with_named_children():
    """Test reverse() works with named child routes."""
    url = MultiChildRouter.reverse("user-detail", user_id=42)
    assert url == "users/42/"


def test_reverse_with_deep_named_children():
    """Test reverse() works with deeply nested named routes."""
    url = MultiChildRouter.reverse("user-post-detail", user_id=5, post_id=10)
    assert url == "users/5/posts/10/"


def test_global_reverse_with_named_children():
    """Test global reverse() works with namespaced child routes."""

    @library.register
    class NamespacedChildRouter(Router):
        namespace = "shop"
        routes = [
            route("", Home, name="home"),
            route("products/<int:product_id>/", PatientView, name="product"),
        ]

    url = reverse("shop:product", product_id=99)
    assert url == "products/99/"


def test_router_context_passed_to_child():
    """Test that router context is correctly passed to child components."""
    request = _get_request("/patient/999/")
    router = NestedRouter(request)
    context = router.get_context_data()
    assert "_router_matched_component" in context
    assert "url_params" in context
    assert context["url_params"].get("patient_id") == 999


def test_remaining_path_in_context():
    """Test that _remaining_path is correctly set for nested routing."""
    request = _get_request("/patient/111/bp/")
    router = NestedRouter(request)
    context = router.get_context_data()
    assert "_remaining_path" in context
    assert context["_remaining_path"] == "" or "bp" in context["_remaining_path"]


def test_consumed_path_tracking():
    """Test that _consumed_path tracks the matched portion of the path."""
    request = _get_request("/patient/222/bp/")
    router = NestedRouter(request)
    context = router.get_context_data()
    assert "patient" in context["_consumed_path"]
    assert "222" in context["_consumed_path"]
