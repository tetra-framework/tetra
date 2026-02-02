import logging

from typing import Set
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, AbstractUser
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.sessions.backends.file import SessionStore

from tetra.exceptions import ProtocolError

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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user: AbstractUser | None = None
        self.session: SessionStore | None = None
        self.component_id: str | None = None
        self.subscribed_groups: Set[str] = set()
        user_model = get_user_model()
        self.user_prefix = f"{user_model._meta.app_label}.{user_model._meta.model_name}"

    async def connect(self) -> None:
        """
        Establish WebSocket connection and auto-subscribe to user, session, and broadcast groups.

        Closes connection if no session is available.
        """
        # Connect to session-specific channel
        self.session = self.scope.get("session")
        if not self.session:
            # Handle case where session is not available
            # There is no channels connection possible then.
            await self.close()
            return

        await self.accept()

        # Auto subscriptions: user, session, broadcast

        # subscribe client to user-specific group if authenticated
        self.user = self.scope.get("user", AnonymousUser())
        if self.user.is_authenticated:
            await self.channel_layer.group_add(
                f"{self.user_prefix}.{self.user.id}", self.channel_name
            )
            self.subscribed_groups.add(f"{self.user_prefix}.{self.user.id}")
            logger.debug(
                f"Subscribed '{self.channel_name}' to '{self.user_prefix}.{self.user.id}' group."
            )

        # session keys theoretically could be None in an invalid session.
        if self.session.session_key:
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

    async def disconnect(self, code) -> None:
        """Disconnects from all subscribed groups."""
        for group in self.subscribed_groups:
            await self.channel_layer.group_discard(group, self.channel_name)
            logger.debug(f"Discarded '{self.channel_name}' from '{group}' group.")
        # remove all subscribed groups after disconnect
        self.subscribed_groups.clear()

    async def receive_json(self, content, **kwargs):
        """Handle incoming JSON messages.

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

    async def _send_unified_message(
        self, message_type: str, payload: dict, metadata: dict | None = None
    ) -> None:
        """Send a message using the unified Tetra protocol."""
        await self.send_json(
            {
                "protocol": "tetra-1.0",
                "type": message_type,
                "payload": payload,
                "metadata": metadata or {},
            }
        )

    async def _handle_subscribe(self, data: dict[str, str]) -> None:
        """Handles subscription requests to named groups."""
        group_name = data.get("group", "")
        if not group_name:
            await self._send_unified_message(
                "subscription.response",
                {
                    "group": group_name,
                    "status": "error",
                    "message": "Invalid group name",
                },
            )
            return

        # TODO: check if group name is valid, in a registry

        if group_name.startswith(f"{self.user_prefix}."):
            # The group name must be exactly {user_prefix}.{user_id}
            # to be considered a user-specific group.
            parts = group_name[len(self.user_prefix) + 1 :].split(".")
            if len(parts) == 1:
                user_id = parts[0]
                # TODO: admin group instead of is_superuser
                if (
                    self.user
                    and str(self.user.id) != user_id
                    and not self.user.is_superuser
                ):
                    logger.warning(
                        f"Unauthorized access to group {group_name} by user "
                        f"{self.user.id if self.user else None} blocked."
                    )
                    await self._send_unified_message(
                        "subscription.response",
                        {
                            "group": group_name,
                            "status": "error",
                            "message": "Unauthorized",
                        },
                    )
                    return

        if group_name.startswith("session."):
            # you cannot manually subscribe to a session group.
            # While we could check against the current valid session key, it is way
            # too dangerous, enabling XSS attacks. So deny that completely.
            logger.warning(
                f"Unauthorized access to group {group_name} by session "
                f"{self.session.session_key if self.session else None} blocked."
            )
            await self._send_unified_message(
                "subscription.response",
                {
                    "group": group_name,
                    "status": "error",
                    "message": "No manually joining of session groups allowed.",
                },
            )
            return

        # check if we already subscribed to this group - if so, send "resubscribed"
        if group_name in self.subscribed_groups:
            await self._send_unified_message(
                "subscription.response",
                {
                    "group": group_name,
                    "status": "resubscribed",
                },
            )
            return

        # Join channel group
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.subscribed_groups.add(group_name)
        await self._send_unified_message(
            "subscription.response",
            {
                "group": group_name,
                "status": "subscribed",
            },
        )

    async def _handle_unsubscribe(self, data: dict[str, str]) -> None:
        group_name = data.get("group")

        if group_name in self.subscribed_groups:
            await self.channel_layer.group_discard(group_name, self.channel_name)
            self.subscribed_groups.remove(group_name)
            await self._send_unified_message(
                "subscription.response",
                {
                    "group": group_name,
                    "status": "unsubscribed",
                },
            )

    async def subscription_response(self, event) -> None:
        """Handle confirmation of subscription from channel layer"""
        # The event should already be in tetra-1.0 protocol format
        if event.get("protocol") == "tetra-1.0":
            await self.send_json(event)
        else:
            # Fallback: wrap in protocol format if needed for backwards compatibility
            await self._send_unified_message(
                "subscription.response",
                {
                    "group": event["group"],
                    "status": event["status"],
                    "message": event.get("message", ""),
                },
            )

    async def component_data_changed(self, event) -> None:
        """Handle component data update

        This method is automatically called when a message is sent via group_send
        with the type "component.data_changed". It checks if the component has matching fields
        and if so, sends the message to the client via websocket.
        """

        # Always send the update to the client. The client-side Tetra.js will
        # find the matching components and update them.
        # Filtering on the server side is problematic because the WebSocket
        # worker might not have access to the component instances that were
        # created during the HTTP request.
        await self._send_unified_message(
            "component.data_changed",
            {
                "group": event["group"],
                "data": event["data"],
                "sender_id": event.get("sender_id"),
            },
        )

    async def component_removed(self, event) -> None:
        """Handle component removal"""
        await self._send_unified_message(
            "component.removed",
            {
                "group": event["group"],
                "component_id": event.get("component_id"),
                "target_group": event.get("target_group"),
                "sender_id": event.get("sender_id"),
            },
        )

    async def component_created(self, event) -> None:
        """Handle component addition"""
        await self._send_unified_message(
            "component.created",
            {
                "group": event["group"],
                "data": event.get("data"),
                "component_id": event.get("component_id"),
                "target_group": event.get("target_group"),
                "sender_id": event.get("sender_id"),
            },
        )

    async def notify(self, event) -> None:
        """Handle notification"""
        type = event.pop("type")
        await self._send_unified_message(type, event)
