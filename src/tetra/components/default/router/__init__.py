from typing import Optional, Any

from django.utils.functional import lazy

from tetra import Component, public
from tetra.router import Route, _route_registry, NestedRoute


class Router(Component):
    """
    A component that manages navigation and dynamic component switching.

    Routing format:
    routes = [route('/', Home), route('about/', About)]

    Router subclasses should define their own template and use {% router_view %}
    to mark where the matched child component should be rendered.
    """

    routes: list[Route] = []
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

    # FIXME: deprecated
    @classmethod
    def get_routes(cls) -> list[Route]:
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

    def _match_route(self, path: str) -> Optional[tuple[str, dict[str, Any]]]:
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
