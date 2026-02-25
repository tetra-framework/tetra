import re
from typing import Optional, Union, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field

from django.conf import settings
from django.urls import path as django_path, re_path as django_re_path
from django.urls.resolvers import RoutePattern, RegexPattern, URLPattern
from django.utils.functional import lazy
from tetra import BasicComponent

if TYPE_CHECKING:
    from tetra.components.default.router import Router


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
        re_path(r'^patient/(?P<id>\\d+)/$', PatientView)
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


def router_view(router_class: type["Router"], template_name: str = None):
    """
    Create a Django view that renders a "root" Router component for any path.

    It is the entry point for server-side rendering (SSR) of client-side routing - when
    users navigate directly to a deep URL (e.g., via bookmark or F5 refresh),
    the server can render the appropriate component based on the Router's route
    configuration.

    Args:
        router_class: The "root" Router component class that handles routing
        template_name: Optional Django template that wraps the router component.
                      If not provided, it renders only the router component.

    Returns:
        A Django view function that can be used in urls.py

    Example:
        # In your Django app's views.py:
        from django.urls import path
        from tetra.router import router_view
        from .components import AppRouter

        app_router_view = router_view(AppRouter, 'base.html')
        urlpatterns = [
            path(...),  # your other paths: API, etc.
            path('', app_router_view),            # Root path
            path('<path:path>', app_router_view), # Catch-all for any subpath
        ]

        # Or use the helper function:
        from tetra.router import router_url

        urlpatterns = [
            router_url('', AppRouter, 'base.html'),
        ]
    """
    from django.shortcuts import render
    from django.http import HttpRequest

    def view(request: HttpRequest, path: str = ""):
        # Normalize path to include leading slash
        if not path.startswith("/"):
            path = "/" + path
        if not path.endswith("/") and settings.APPEND_SLASH:
            path = path + "/"

        # Render the router component with the current path
        router_html = router_class.as_tag(request)
        print("SSR:", router_class.__name__)

        if template_name:
            # Render within a Django template
            return render(
                request,
                template_name,
                {
                    "router": router_html,
                    "router_component": router_class,
                },
            )
        else:
            # Render just the router component
            from django.http import HttpResponse

            return HttpResponse(router_html)

    return view


def router_url(
    base_path: str,
    router_class: type["Router"],
    template_name: str = None,
    name: str = None,
):
    """
    Create Django URL patterns for a Router component with catch-all routing.

    This is a convenience function that creates the necessary URL patterns to
    handle both the base path and all subpaths for client-side routing with SSR.

    Args:
        base_path: The base URL path where the router is mounted (e.g., '', 'app/', 'users/')
        router_class: The Router component class that handles routing
        template_name: Optional Django template that wraps the router component
        name: Optional URL pattern name

    Returns:
        A list of Django URLPattern objects to include in urlpatterns

    Example:
        # In urls.py:
        from django.urls import path, include
        from tetra.router import router_url
        from myapp.components import AppRouter

        urlpatterns = [
            # Other URL patterns...
            *router_url('', AppRouter, 'base.html', name='app'),
        ]

        # This creates two patterns:
        # 1. path('', router_view) - handles the base path
        # 2. path('<path:path>', router_view) - catches all subpaths
    """
    view = router_view(router_class, template_name)

    # Normalize base_path
    if base_path and not base_path.endswith("/"):
        base_path = base_path + "/"

    patterns = []

    # Pattern for base path
    if base_path == "" or base_path == "/":
        # Root router
        patterns.append(django_path("", view, name=name))
        patterns.append(django_path("<path:path>", view))
    else:
        # Nested base path
        patterns.append(django_path(base_path, view, name=name))
        patterns.append(django_path(f"{base_path}<path:path>", view))

    return patterns
