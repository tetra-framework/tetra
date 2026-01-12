import re

from django.conf import settings
from sourcetypes import django_html
from tetra import Component, public


def ensure_trailing_slash(path):
    if settings.APPEND_SLASH:
        return path if path.endswith("/") else path + "/"
    return path


class Router(Component):
    """
    A component that manages navigation and dynamic component switching.
    """

    routes = {}  # Map of path patterns to component names.
    current_component = public("")
    current_path = public("")

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

    def load(self):
        if not self.current_component:
            self.navigate(self.request.path, push=False)

    @public
    def navigate(self, path, push=True):
        if push:
            self.client._pushUrl(path)

        self.current_path = path
        component_name = self._match_route(path)

        if component_name:
            self.current_component = component_name
        else:
            self.current_component = ""

    def _match_route(self, path):
        path = ensure_trailing_slash(path)

        # Exact match
        if path in self.routes:
            return self.routes[path]

        # Regex match
        for pattern, component_name in self.routes.items():
            if re.match(f"^{pattern}$", path):
                return component_name

        return None


class Link(Component):
    """
    A component for navigating between routes.
    """

    to = ""
    label = ""
    active_class = "active"

    # language=html
    template = """
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

    to = ""

    template = "<div></div>"

    def load(self, to):
        self.to = to

    def render(self, *args, **kwargs):
        self.client._dispatch("tetra:navigate", {"path": self.to})
        return super().render(*args, **kwargs)
