import re
from typing import Optional

from django.conf import settings
from sourcetypes import django_html
from tetra import Component, public, BasicComponent


def ensure_trailing_slash(path):
    if settings.APPEND_SLASH:
        return path if path.endswith("/") else path + "/"
    return path


class Router(Component):
    """
    A component that manages navigation and dynamic component switching.
    """

    # Map of path patterns to components.
    routes: dict[str, str | type[BasicComponent]] = {}

    current_component: str = public("")
    current_path: str = public("")

    # language=html
    template: django_html = """
    <div
        @popstate.window="navigate(window.location.pathname, false)"
        @tetra:navigate.window="navigate($event.detail.path)"
    >
        {% if current_component %}
            {% component =current_component / %}
        {% else %}
            {% slot "default" %}{% endslot %}
        {% endif %}
    </div>
    """

    def load(self, *args, **kwargs):
        if not self.current_component:
            self.navigate(self.request.path, push=False)

    @public
    def navigate(self, path, push=True):
        if push:
            self.client._pushUrl(path)

        self.current_path = path
        component_name = self._match_route(path)
        self.current_component = component_name or ""

    def _match_route(self, path) -> str:
        path = ensure_trailing_slash(path)

        # Exact match
        if path in self.routes:
            component = self.routes[path]
            if isinstance(component, str):
                return component
            return f"{component._library.name}.{component.__name__}"

        # Regex match
        for pattern, component in self.routes.items():
            if re.match(f"^{pattern}$", path):
                if isinstance(component, str):
                    return component
                return f"{component._library.name}.{component.__name__}"

        return ""


class Link(Component):
    """
    A component for navigating between routes.
    """

    to: str = ""
    label: str = ""
    active_class: str = "active"

    # language=html
    template: django_html = """
    <a
        {% ... attrs %}
        href="{{ to }}"
        @click.prevent="click()"
        :class="{ '{{ active_class }}': window.location.pathname === '{{ to }}' }"
    >
        {% if label %}{{ label }}{% else %}{% slot "default" %}{% endslot %}{% endif %}
    </a>
    """

    def load(self, to="#", label="", active_class="active", *args, **kwargs):
        self.to = to
        self.label = label
        self.active_class = active_class

    @public(update=False)
    def click(self):
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
