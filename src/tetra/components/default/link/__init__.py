from sourcetypes import django_html

from tetra import Component, BasicComponent


class Link(BasicComponent):
    """
    A component for navigating between routes.
    """

    to: str = ""
    active_class: str = "active"

    def load(self, to="#", active_class="active", *args, **kwargs):
        self.to = to
        self.active_class = active_class

    # @public(update=False)
    # def follow(self):
    #     self.client._dispatch("tetra:navigate", {"path": self.to})
