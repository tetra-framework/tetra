from sourcetypes import django_html

from tetra import Component


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
