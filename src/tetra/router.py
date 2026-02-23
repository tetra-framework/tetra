import re
from typing import Optional, Union, List, Dict, Any
from dataclasses import dataclass, field

from django.conf import settings
from django.urls import path as django_path, re_path as django_re_path
from django.urls.resolvers import RoutePattern, RegexPattern, URLPattern
from django.utils.functional import lazy
from sourcetypes import django_html
from tetra import Component, public, BasicComponent


# Global route registry
class RouteRegistry:
    """
    Global registry for all Tetra routes across all Router components.

    Allows route lookup by name with optional namespace, similar to Django's URL resolver.
    """

    def __init__(self):
        self._routes: Dict[str, tuple[type["Router"], "Route"]] = {}

    def register(
        self,
        router_class: type["Router"],
        route_obj: "Route",
        namespace: Optional[str] = None,
    ):
        """
        Register a route with optional namespace.

        Args:
            router_class: The Router class that owns this route
            route_obj: The Route object to register
            namespace: Optional namespace (e.g., 'user', 'admin')
        """
        if not route_obj.name:
            return  # Skip unnamed routes

        # Build full name with namespace if provided
        if namespace:
            full_name = f"{namespace}:{route_obj.name}"
        else:
            full_name = route_obj.name

        if full_name in self._routes:
            existing_router, _ = self._routes[full_name]
            # Only warn if it's a different router (allow re-registration from same router)
            if existing_router != router_class:
                import warnings

                warnings.warn(
                    f"Route name '{full_name}' is already registered by {existing_router.__name__}. "
                    f"It will be overwritten by {router_class.__name__}.",
                    stacklevel=2,
                )

        self._routes[full_name] = (router_class, route_obj)

    def get(self, name: str) -> Optional[tuple[type["Router"], "Route"]]:
        """Get a route by name (with optional namespace)."""
        return self._routes.get(name)

    def reverse(self, name: str, **kwargs) -> str:
        """
        Reverse a named route to a URL path.

        Args:
            name: Route name, optionally with namespace (e.g., 'user:profile')
            **kwargs: URL parameters for the route

        Returns:
            The URL path for the named route

        Raises:
            ValueError: If the route name is not found
        """
        result = self.get(name)
        if not result:
            raise ValueError(f"Route '{name}' not found in global registry")

        router_class, route_obj = result
        # Use the router's reverse logic
        return router_class._reverse_route(route_obj, **kwargs)

    def reverse_lazy(self, name: str, **kwargs):
        """Lazy version of reverse()."""
        return lazy(self.reverse, str)(name, **kwargs)

    def clear(self):
        """Clear all registered routes (useful for testing)."""
        self._routes.clear()


# Global instance
_route_registry = RouteRegistry()


def reverse(name: str, **kwargs) -> str:
    """
    Global function to reverse a named Tetra route to a URL path.

    Works like Django's reverse() but for Tetra component routes.
    Supports namespaced routes (e.g., 'user:profile').

    Args:
        name: Route name, optionally with namespace (e.g., 'user:profile')
        **kwargs: URL parameters for the route

    Returns:
        The URL path for the named route

    Raises:
        ValueError: If the route name is not found

    Example:
        url = reverse('user:profile', user_id=123)
    """
    return _route_registry.reverse(name, **kwargs)


def reverse_lazy(name: str, **kwargs):
    """
    Lazy version of reverse() for Tetra routes.

    Useful when you need to define URLs at import time.

    Example:
        SUCCESS_URL = reverse_lazy('home')
    """
    return _route_registry.reverse_lazy(name, **kwargs)


def ensure_trailing_slash(path):
    if settings.APPEND_SLASH:
        return path if path.endswith("/") else path + "/"
    return path


@dataclass
class Route:
    """
    Represents a route that maps a URL pattern to a component.

    Uses Django's URL pattern infrastructure for matching and parameter extraction.
    """

    pattern: Union[RoutePattern, RegexPattern, str]
    component: Union[str, type[BasicComponent]]
    name: Optional[str] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)

    # For nested routing - child routes under this route
    children: Optional[List["Route"]] = None

    # Internal: compiled URL pattern
    _url_pattern: Optional[URLPattern] = None
    _prefix: str = ""

    def __post_init__(self):
        """Compile the URL pattern after initialization."""
        if isinstance(self.pattern, str):
            # Convert string patterns to Django patterns
            # Strip leading slash - Django patterns don't use them
            pattern = self.pattern.lstrip("/")

            # Detect if this is a regex pattern (contains regex special chars)
            is_regex = bool(re.search(r"[\\()[\]{}?+*|^$.]", pattern))

            if is_regex:
                # Use regex pattern
                self._url_pattern = django_re_path(
                    pattern, lambda: None, name=self.name
                )
            else:
                # Use RoutePattern (path-style) by default
                self._url_pattern = django_path(pattern, lambda: None, name=self.name)
        elif isinstance(self.pattern, (RoutePattern, RegexPattern)):
            # Already a Django pattern
            self._url_pattern = URLPattern(self.pattern, lambda: None, name=self.name)
        elif isinstance(self.pattern, URLPattern):
            self._url_pattern = self.pattern

    def match(self, path: str) -> Optional[tuple[str, Dict[str, Any]]]:
        """
        Try to match the given path against this route's pattern.

        Returns:
            Tuple of (component_name, url_params) if matched, None otherwise.
        """
        if not self._url_pattern:
            return None

        # Normalize path for matching
        normalized_path = ensure_trailing_slash(path) if path else "/"

        # Try to resolve the path
        try:
            match = self._url_pattern.resolve(normalized_path.lstrip("/"))
            if match:
                # Get component name
                component_name = self._get_component_name()
                return component_name, match.kwargs
        except Exception:
            pass

        return None

    def match_prefix(self, path: str) -> Optional[tuple[str, str, Dict[str, Any]]]:
        """
        Match path and return remaining path for nested routing.

        Returns:
            Tuple of (component_name, remaining_path, url_params) if matched, None otherwise.
        """
        if not self._url_pattern:
            return None

        normalized_path = ensure_trailing_slash(path) if path else "/"
        path_to_match = normalized_path.lstrip("/")

        # For patterns, we need to check if we have a partial match
        pattern = self._url_pattern.pattern

        # Build regex from pattern
        if hasattr(pattern, "regex"):
            # Django's URLPattern has a regex that ends with \Z (end of string)
            # For prefix matching, we need to remove that anchor
            regex_pattern = pattern.regex.pattern
            # Remove end-of-string anchors (\Z, \z, $) for prefix matching
            if regex_pattern.endswith(r"\Z"):
                regex_pattern = regex_pattern[:-2]
            elif regex_pattern.endswith(r"\z"):
                regex_pattern = regex_pattern[:-2]
            elif regex_pattern.endswith("$"):
                regex_pattern = regex_pattern[:-1]
            regex = re.compile(regex_pattern)
        elif hasattr(pattern, "_route"):
            # RoutePattern - convert to regex
            route_regex = pattern._route
            # Simple conversion for common patterns
            route_regex = route_regex.replace("<int:", "(?P<").replace(">", r">\d+)")
            route_regex = route_regex.replace("<str:", "(?P<").replace(">", r">[^/]+)")
            route_regex = route_regex.replace("<slug:", "(?P<").replace(
                ">", r">[-\w]+)"
            )
            route_regex = route_regex.replace("<uuid:", "(?P<").replace(
                ">", r">[0-9a-f-]+)"
            )
            route_regex = route_regex.replace("<path:", "(?P<").replace(">", r">.+)")
            regex = re.compile(f"^{route_regex}")
        else:
            return None

        # Try to match
        match = regex.match(path_to_match)
        if match:
            matched_length = match.end()
            remaining_path = path_to_match[matched_length:]
            component_name = self._get_component_name()
            return component_name, remaining_path, match.groupdict()

        return None

    def _get_component_name(self) -> str:
        """Get the fully qualified component name."""
        if isinstance(self.component, str):
            return self.component
        return f"{self.component._library.name}.{self.component.__name__}"


@dataclass
class NestedRoute(Route):
    """
    A route that contains child routes for nested routing.

    When this route matches, it can either:
    1. Have explicit children routes
    2. Delegate to a child Router component (delegation pattern)
    """

    child_router: Optional[type["Router"]] = None

    def __post_init__(self):
        super().__post_init__()
        # NestedRoute can have children, be a delegating route, or both
        # No validation needed - it's valid to have neither if component is a Router


def route(
    pattern: str,
    component: Union[str, type[BasicComponent]],
    name: Optional[str] = None,
    children: Optional[List[Route]] = None,
    delegate: bool = False,
    **kwargs,
) -> Route:
    """
    Create a route using path-style pattern (e.g., 'patient/<int:id>/').

    Args:
        pattern: URL pattern using Django's path syntax
        component: Component class or string reference
        name: Optional name for the route
        children: Optional list of child routes for nested routing (explicit pattern)
        delegate: If True and component is a Router, delegate remaining path to it
        **kwargs: Additional keyword arguments passed to the component

    Examples:
        # Simple route
        route('', Home)

        # Route with URL parameters
        route('patient/<int:id>/', PatientView)

        # Explicit nested routing (parent knows grandchildren)
        route('patients/', PatientList, children=[
            route('<int:id>/', PatientView),
            route('<int:id>/bp/', BloodPressureView),
        ])

        # Delegated routing (component is itself a Router)
        route('patient/<int:patient_id>/', PatientRouter, delegate=True)
    """
    if children or delegate:
        return NestedRoute(
            pattern=pattern,
            component=component,
            name=name,
            kwargs=kwargs,
            children=children,
        )
    return Route(pattern=pattern, component=component, name=name, kwargs=kwargs)


def path(
    pattern: str,
    component: Union[str, type[BasicComponent]],
    name: Optional[str] = None,
    routes: Optional[List[Route]] = None,
    **kwargs,
) -> Route:
    """
    Alias for route() - creates a route using Django's path syntax.

    This provides a more Django-like API.
    """
    return route(pattern, component, name=name, children=routes, **kwargs)


def re_path(
    pattern: str,
    component: Union[str, type[BasicComponent]],
    name: Optional[str] = None,
    routes: Optional[List[Route]] = None,
    **kwargs,
) -> Route:
    """
    Create a route using regex pattern.

    Args:
        pattern: Regular expression pattern
        component: Component class or string reference
        name: Optional name for the route
        routes: Optional list of child routes for nested routing
        **kwargs: Additional keyword arguments passed to the component

    Examples:
        re_path(r'^patient/(?P<id>\d+)/$', PatientView)
    """
    django_pattern = django_re_path(pattern, lambda: None, name=name)
    if routes:
        return NestedRoute(
            pattern=django_pattern.pattern,
            component=component,
            name=name,
            kwargs=kwargs,
            children=routes,
        )
    return Route(
        pattern=django_pattern.pattern, component=component, name=name, kwargs=kwargs
    )


def include(routes: List[Route]) -> List[Route]:
    """
    Include a list of routes.

    This is mainly for readability and Django-like syntax.
    Used with nested routing.

    Example:
        route('patients/', include([
            route('<int:id>/', PatientView),
            route('<int:id>/bp/', BloodPressureView),
        ]))
    """
    return routes


class Router(Component):
    """
    A component that manages navigation and dynamic component switching.

    Routing format:
    routes = [route('/', Home), route('about/', About)]

    Router subclasses should define their own template and use {% router_view %}
    to mark where the matched child component should be rendered.
    """

    routes: List[Route] = []
    namespace: Optional[str] = None  # Optional namespace for route registration

    # Internal routing state (not exposed to frontend)
    _matched_component: str = ""
    _consumed_path: str = ""
    _remaining_path: str = ""

    # Public state for templates
    current_path: str = public("")
    url_params: dict[str, Any] = public({})

    @property
    def current_component(self) -> str:
        """
        Backward compatibility property for accessing matched component.

        Returns the fully qualified name of the currently matched component.
        """
        return self._matched_component

    @current_component.setter
    def current_component(self, value: str):
        """Allow setting current_component for backward compatibility."""
        self._matched_component = value

    def __init_subclass__(cls, **kwargs):
        """Auto-register routes when Router subclass is defined."""
        super().__init_subclass__(**kwargs)
        # Register all named routes in the global registry
        cls._register_routes()

    @classmethod
    def get_routes(cls) -> List[Route]:
        return cls.routes

    @classmethod
    def _register_routes(cls):
        """Register all routes from this Router in the global registry."""
        for route_obj in cls.get_routes():
            _route_registry.register(cls, route_obj, namespace=cls.namespace)
            # Also register nested children
            if isinstance(route_obj, NestedRoute) and route_obj.children:
                for child_route in route_obj.children:
                    _route_registry.register(cls, child_route, namespace=cls.namespace)

    @classmethod
    def reverse(cls, name: str, **kwargs) -> str:
        """
        Reverse a named route to a URL path.

        Args:
            name: The name of the route to reverse
            **kwargs: URL parameters for the route (e.g., patient_id=123)

        Returns:
            The URL path for the named route

        Raises:
            ValueError: If the route name is not found

        Example:
            class MyRouter(Router):
                routes = [
                    route('', Home, name='home'),
                    route('patient/<int:id>/', PatientView, name='patient-detail'),
                ]

            # Reverse by name
            url = MyRouter.reverse('patient-detail', id=123)
            # Returns: 'patient/123/'
        """
        for route_obj in cls.routes:
            if route_obj.name == name:
                # Use Django's reverse logic on the pattern
                if route_obj._url_pattern:
                    try:
                        # Django's URLPattern.reverse() or pattern.reverse()
                        if hasattr(route_obj._url_pattern.pattern, "reverse"):
                            path = route_obj._url_pattern.pattern.reverse(**kwargs)
                        else:
                            # Fallback: manually construct path for simple patterns
                            path = str(route_obj._url_pattern.pattern)
                            for key, value in kwargs.items():
                                path = path.replace(f"<int:{key}>", str(value))
                                path = path.replace(f"<str:{key}>", str(value))
                                path = path.replace(f"<slug:{key}>", str(value))
                                path = path.replace(f"<uuid:{key}>", str(value))
                                path = path.replace(f"<path:{key}>", str(value))
                        return path
                    except Exception as e:
                        raise ValueError(
                            f"Could not reverse route '{name}' with kwargs {kwargs}: {e}"
                        )
            # Check nested routes recursively
            if isinstance(route_obj, NestedRoute) and route_obj.children:
                for child_route in route_obj.children:
                    if child_route.name == name:
                        # For nested routes, combine parent and child patterns
                        parent_path = cls._reverse_route(route_obj, **kwargs)
                        child_path = cls._reverse_route(child_route, **kwargs)
                        return parent_path.rstrip("/") + "/" + child_path.lstrip("/")

        raise ValueError(f"Route '{name}' not found in {cls.__name__}")

    @classmethod
    def _reverse_route(cls, route_obj: Route, **kwargs) -> str:
        """Helper to reverse a single route object."""
        if not route_obj._url_pattern:
            return ""
        try:
            if hasattr(route_obj._url_pattern.pattern, "reverse"):
                return route_obj._url_pattern.pattern.reverse(**kwargs)
            else:
                # Fallback: manually construct path
                path = str(route_obj._url_pattern.pattern)
                for key, value in kwargs.items():
                    path = path.replace(f"<int:{key}>", str(value))
                    path = path.replace(f"<str:{key}>", str(value))
                    path = path.replace(f"<slug:{key}>", str(value))
                    path = path.replace(f"<uuid:{key}>", str(value))
                    path = path.replace(f"<path:{key}>", str(value))
                return path
        except Exception:
            return ""

    @classmethod
    def reverse_lazy(cls, name: str, **kwargs):
        """
        Lazy version of reverse() that defers evaluation until the value is accessed.

        This is useful when you need to provide a URL at import time, but the
        route definitions may not be fully loaded yet.

        Args:
            name: The name of the route to reverse
            **kwargs: URL parameters for the route (e.g., patient_id=123)

        Returns:
            A lazy object that evaluates to the URL path when accessed

        Example:
            class MyRouter(Router):
                routes = [
                    route('', Home, name='home'),
                ]

            # At import time
            SUCCESS_URL = MyRouter.reverse_lazy('home')
        """
        return lazy(cls.reverse, str)(name, **kwargs)

    # Pass routing context to child components
    _extra_context = [
        "url_params",
        "_router_matched_component",
        "_remaining_path",
        "_consumed_path",
    ]

    # language=html
    template: django_html = """
    <div>
        {% router_view %}
    </div>
    """

    # Alpine.js event handlers for navigation (added dynamically to root element)
    # language=javascript
    script = """
    return {
        __rootBind: {
            '@popstate.window': 'navigate(window.location.pathname, false)',
            '@tetra:navigate.window': 'navigate($event.detail.path)',
        }
    }
    """

    def load(self, *args, **kwargs):
        # Ensure url_params is initialized even if passed from parent context
        if "url_params" not in kwargs and not hasattr(self, "url_params"):
            self.url_params = {}

        # Merge parent url_params if passed via context
        if hasattr(self, "_context") and self._context:
            parent_params = self._context.get("url_params", {})
            if parent_params and isinstance(parent_params, dict):
                # Merge parent params with current params (current takes precedence)
                self.url_params = {**parent_params, **self.url_params}

        # Initialize routing state
        if not self._matched_component:
            # Use browser URL from request.tetra as source of truth, not request.path
            path = self.request.tetra.current_url_path or self.request.path

            # If this is a nested router, use the remaining path from parent
            if (
                hasattr(self, "_context")
                and self._context
                and "_remaining_path" in self._context
            ):
                path_to_match = self._context["_remaining_path"]
                self.navigate(path_to_match, push=False)
            else:
                self.navigate(path, push=False)

    def get_context_data(self, **kwargs):
        """
        Override to add routing context to template.

        This exposes routing state to the template so {% router_view %} can access it.
        """
        context = super().get_context_data(**kwargs)

        # Add routing context
        context.update(
            {
                "_router_matched_component": self._matched_component,
                "_remaining_path": self._remaining_path,
                "_consumed_path": self._consumed_path,
                "url_params": self.url_params,
            }
        )

        return context

    @public
    def navigate(self, path: str, push=True):
        if push:
            self.client._pushUrl(path)

        self.current_path = path

        # Update request.tetra URL so current_url_path reflects the navigation
        # This ensures route matching uses the correct path
        self.request.tetra.set_url_path(path)

        # Use browser URL as source of truth for routing
        path_to_match = self.request.tetra.current_url_path or path

        # If this is a nested router, only match against remaining path
        if (
            hasattr(self, "_context")
            and self._context
            and "_remaining_path" in self._context
        ):
            path_to_match = self._context["_remaining_path"]

        result = self._match_route(path_to_match)

        if result:
            component_name, url_params = result
            self._matched_component = component_name

            # Merge with parent url_params if this is a nested router
            if hasattr(self, "_context") and self._context:
                parent_params = self._context.get("url_params", {})
                if parent_params and isinstance(parent_params, dict):
                    # Merge parent params with current params (current takes precedence)
                    self.url_params = {**parent_params, **url_params}
                else:
                    self.url_params = url_params
            else:
                self.url_params = url_params

            # Store in request.tetra for all components to access
            # Also merge with existing params to preserve parent router params
            existing_params = (
                self.request.tetra.route_params
                if hasattr(self.request.tetra, "route_params")
                else {}
            )
            merged_params = {**existing_params, **self.url_params}
            self.request.tetra.set_route_params(merged_params)
        else:
            self._matched_component = ""
            self.url_params = {}
            # Don't clear request.tetra params - child routers might need parent params
            # self.request.tetra.set_route_params({})

    def _match_route(self, path: str) -> Optional[tuple[str, Dict[str, Any]]]:
        """
        Match path against list of Route objects.

        For nested routing, stores consumed and remaining path portions
        that can be passed to child Router components.
        """
        for route_obj in self.routes:
            # First try exact match
            result = route_obj.match(path)
            if result:
                component_name, url_params = result
                # Exact match - this router consumes entire path
                self._consumed_path = path
                self._remaining_path = ""
                return result

            # If this is a NestedRoute, try prefix matching
            if isinstance(route_obj, NestedRoute):
                prefix_result = route_obj.match_prefix(path)

                if prefix_result:
                    component_name, remaining_path, url_params = prefix_result

                    # Calculate consumed path
                    if remaining_path:
                        consumed_length = len(path) - len(remaining_path)
                        self._consumed_path = path[:consumed_length]
                        self._remaining_path = remaining_path
                    else:
                        self._consumed_path = path
                        self._remaining_path = ""

                    # If there's no remaining path, this route is the match
                    if not remaining_path or remaining_path == "/":
                        return component_name, url_params

                    # If this route has explicit children, try to match them
                    if route_obj.children:
                        for child_route in route_obj.children:
                            child_result = child_route.match(remaining_path)
                            if child_result:
                                # Merge parent and child URL parameters
                                merged_params = {**url_params, **child_result[1]}
                                # Update consumed/remaining for explicit child match
                                self._consumed_path = path
                                self._remaining_path = ""
                                return child_result[0], merged_params

                    # If no children matched but there's remaining path,
                    # the component itself should handle it (delegation pattern)
                    # In this case, still return the parent component and let it
                    # route internally
                    if remaining_path and remaining_path != "/":
                        # Component will receive remaining path and route internally
                        return component_name, url_params

        # No match found
        self._consumed_path = ""
        self._remaining_path = ""
        return None


class Link(Component):
    """
    A component for navigating between routes.
    """

    to: str = ""
    active_class: str = "active"

    # language=html
    template: django_html = """
    <a {% ... attrs %}
       href="{{ to }}"
       @click.prevent="follow()"
       :class="{ '{{ active_class }}': window.location.pathname === '{{ to }}' }"
    >
        {% slot default %}{% endslot %}
    </a>
    """

    def load(self, to="#", active_class="active", *args, **kwargs):
        self.to = to
        self.active_class = active_class

    @public(update=False)
    def follow(self):
        self.client._dispatch("tetra:navigate", {"path": self.to})


class Redirect(Component):
    """
    A component that redirects to another path when rendered.
    """

    to: str = ""

    template: django_html = "<div></div>"

    def load(self, to: str, *args, **kwargs):
        self.to = to

    def render(self, *args, **kwargs):
        self.client._dispatch("tetra:navigate", {"path": self.to})
        return super().render(*args, **kwargs)
