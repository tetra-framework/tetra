from asgiref.sync import async_to_sync

import tetra.globals
from .base import Component, public
from .subscription import registry
from ..dispatcher import ComponentDispatcher


# Global flag to track if reactive components are registered

# a registry to keep track of all reactive components instances


class ReactiveComponent(Component):
    """A component that automatically connects to a channel and receives push
    notifications."""

    __abstract__ = True
    group_subscription: str = ""

    def __init_subclass__(cls, **kwargs):
        """Initialize the reactive component."""
        super().__init_subclass__(**kwargs)

        # set a global flag to indicate that reactive components are in use
        tetra.globals._has_reactive_components = True

    def __init__(self, *args, **kwargs):
        if "subscribe" in kwargs:
            if self.group_subscription:
                raise ValueError(
                    "Subscriptions cannot be defined in both component and template."
                )
            self.group_subscription = kwargs["subscribe"].strip()
        super().__init__(*args, **kwargs)

        # register the component with the channel layer
        # this is a list that can be queried for all reactive components to determine
        # their public_properties when sending data over websockets.
        group_name = self.group_subscription
        if not self.group_subscription in registry:
            registry[group_name] = [self]
        else:
            registry[group_name].append(self)

    def get_extra_tags(self) -> dict[str, str | None]:
        extra_tags = super().get_extra_tags()
        extra_tags["tetra-reactive"] = ""

        # Add subscribe channel groups as data attribute
        if self.group_subscription:
            extra_tags["tetra-subscription"] = self.group_subscription

        return extra_tags

    def get_subscription(self) -> str:
        """Returns the subscribed group for this component.

        This can be overridden to dynamically subscribe to channels when the
        component is created. Per default, it is evaluated once at initialization,
        not with every component cycle's load().
        """
        return self.group_subscription

    @public(update=False)
    def remove_component(self):
        async_to_sync(ComponentDispatcher.component_remove)(
            self.get_subscription(), self.component_id
        )
