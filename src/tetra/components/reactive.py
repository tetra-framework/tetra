from asgiref.sync import async_to_sync
from django.apps import apps

from .base import Component, public
from .subscription import registry
from ..dispatcher import ComponentDispatcher


# Global flag to track if reactive components are registered

# a registry to keep track of all reactive components instances


class ReactiveComponent(Component):
    """A component that automatically connects to a channel and receives push
    notifications."""

    __abstract__ = True
    subscription: str = ""

    def __init_subclass__(cls, **kwargs):
        """Initialize the reactive component."""
        super().__init_subclass__(**kwargs)

        # set a global flag to indicate that reactive components are in use
        from ..utils import check_websocket_support

        if check_websocket_support():
            apps.get_app_config("tetra").has_reactive_components = True
        else:
            raise RuntimeError(
                f"{cls.__name__} is a reactive component, but WebSockets are not supported. "
            )

    def get_extra_tags(self) -> dict[str, str | None]:
        extra_tags = super().get_extra_tags()
        extra_tags["tetra-reactive"] = ""

        # Add subscribe channel group as data attribute
        subscription = self.get_subscription()
        if subscription:
            extra_tags["tetra-subscription"] = subscription

        return extra_tags

    def _pre_load(self, *args, subscribe: str = "", **kwargs):
        """Handle subscription parameter before calling load().

        The subscribe parameter can be passed from the template to dynamically
        set the subscription group for this component instance.
        """
        if subscribe:
            self.subscription = subscribe
        super()._pre_load(*args, **kwargs)

    def get_subscription(self) -> str:
        """Returns the subscribed group for this component.

        This can be overridden to dynamically subscribe to channels when the
        component is created. Per default, it is evaluated once at initialization,
        not with every component cycle's load().
        """
        return self.subscription

    @public(update=False)
    def remove_component(self):
        async_to_sync(ComponentDispatcher.component_removed)(
            self.get_subscription(), self.component_id
        )
