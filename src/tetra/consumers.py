import logging

from typing import Set
from django.contrib.auth.models import AnonymousUser, AbstractUser
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from tetra.components import subscription
from tetra.dispatcher import ComponentDispatcher
from tetra.exceptions import ComponentError
from tetra.utils import TetraWsResponse

logger = logging.getLogger(__name__)


class TetraConsumer(AsyncJsonWebsocketConsumer):
    """
    A consumer that handles WebSocket connections for Tetra.

    The data is sent as JSON to the client in the following format:

        {
          "type": "subscribe|unsubscribe|notify|component_update|component_remove",
          "channel": "channel_name",
          "component_id": "component_id",
          "event_name": "event_name",
          "data": {},
          "sender_id": "sender_id"  # optional
          "status": 200|400,
        }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user: AbstractUser | None = None
        self.session: str | None = None
        self.component_id: str | None = None
        self.subscribed_groups: Set[str] = set()

    async def connect(self):
        """
        Establish WebSocket connection and auto-subscribe to user, session, and broadcast groups.

        Closes connection if no session is available.
        """
        # Connect to session-specific channel
        self.session = self.scope.get("session")
        if not self.session:
            # Handle case where session is not available
            # There is no channels connection feasible then.
            await self.close()
            return

        await self.accept()

        # Auto subscriptions: user, session, broadcast

        # subscribe client to user-specific group if authenticated
        self.user = self.scope.get("user", AnonymousUser())
        if self.user.is_authenticated:
            await self.channel_layer.group_add(
                f"user.{self.user.id}", self.channel_name
            )
            self.subscribed_groups.add(f"user.{self.user.id}")
            logger.debug(
                f"Subscribed '{self.channel_name}' to 'user.{self.user.id}' group."
            )

        # subscribe client to session-specific group
        await self.channel_layer.group_add(
            f"session.{self.session.session_key}", self.channel_name
        )
        self.subscribed_groups.add(f"session.{self.session.session_key}")
        logger.debug(
            f"Subscribed '{self.channel_name}' to 'session.{self.session.session_key}' "
            f"group."
        )

        # Connect to public broadcast group
        await self.channel_layer.group_add("broadcast", self.channel_name)
        self.subscribed_groups.add("broadcast")
        logger.debug(f"Subscribed '{self.channel_name}' to 'broadcast' group.")

    async def disconnect(self, code):
        """
        Disconnects from all subscribed groups.
        """
        for group in self.subscribed_groups:
            await self.channel_layer.group_discard(group, self.channel_name)
            logger.debug(f"Discarded '{self.channel_name}' from '{group}' group.")
        # remove all subscribed groups after disconnect
        self.subscribed_groups.clear()

    async def receive_json(self, content, **kwargs):
        """
        Handle incoming JSON messages.

        This method processes different types of messages based on the 'type' field
        in the received JSON content and routes them to appropriate handler methods.
        Supported message types include 'subscribe', 'unsubscribe', 'notify', and
        'data_request'. Unknown message types are logged as warnings.
        """
        message_type = content.get("type")
        if message_type == "subscribe":
            await self._handle_subscribe(content)
        elif message_type == "unsubscribe":
            await self._handle_unsubscribe(content)
        else:
            logger.warning(
                f"Unknown message type received via websocket: {message_type}"
            )

    async def _handle_subscribe(self, data):
        """Handles subscription requests to named groups."""
        group_name = data.get("group")
        if group_name in self.subscribed_groups:
            return
        if not group_name:
            await ComponentDispatcher.subscription_response(
                group_name, status="error", message="Invalid group name"
            )
            return

        # TODO: check if group name is valid, in a registry

        if group_name.startswith("user."):
            user_id = group_name.split(".")[1]
            # TODO: admin group instead of is_superuser
            if str(self.user.id) != user_id and not self.user.is_superuser:
                logger.warning(
                    f"Unauthorized access to group {group_name} by user "
                    f"{user_id} blocked."
                )
                return

        # Join channel group
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.subscribed_groups.add(group_name)
        await ComponentDispatcher.subscription_response(group_name, status="subscribed")

    async def _handle_unsubscribe(self, data):
        group_name = data.get("group")

        if group_name in self.subscribed_groups:
            await self.channel_layer.group_discard(group_name, self.channel_name)
            await ComponentDispatcher.subscription_response(
                group_name, status="unsubscribed"
            )
            self.subscribed_groups.remove(group_name)

    async def subscription_response(self, event):
        """Handle confirmation of subscription"""
        await self.send_json(event)

    async def component_update_data(self, event):
        """Handle component data update

        This method is automatically called when a message is sent via group_send
        with the type "component.update_data". It checks if the component has matching fields
        and if so, sends the message to the client via websocket.
        """
        group_name = event["group"]
        components = subscription.registry.get(group_name, [])
        for c in components:
            if all(key in c._public_properties for key in event["data"].keys()):
                await self.send_json(event)
            else:
                raise ComponentError(
                    f"No matching components found for "
                    f"channel group data {event['data'].keys()} in '{group_name}'."
                )
        if not components:
            logger.warning(
                f"No matching component found for channel group {group_name}."
            )

    async def component_remove(self, event):
        """Handle component removal"""
        await self.send_json(event)
