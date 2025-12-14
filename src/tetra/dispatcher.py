from channels.layers import get_channel_layer


class ComponentDispatcher:
    """
    A class to dispatch notifications, updates, data and removal requests of
    components to WebSocket connections.

    It provides convenient methods to asynchronously send data to client components.
    Beware that any of the methods are asynchronous and should be called inside an
    asynchronous context. If ou use them from synchronous code, you will need to use
    `async_to_sync` from `asgiref.sync` to convert synchronous code to asynchronous:

    ```python
    from tetra.dispatcher import ComponentDispatcher

    await ComponentDispatcher.update_data(
    # or async_to_sync(ComponentDispatcher.update_data)(
        "notifications.news.headline",
        {
            "headline": "Breaking News!",
        }
    )
    ```
    """

    @staticmethod
    async def notify(group: str, event_name: str, data: dict) -> None:
        """
        Sends a JavaScript notification to all WebSocket connections in a group.

        Args:
           group: WebSocket group name to send the notification to.
           event_name: Name of the event to be sent, in the form "tetra:some-event"
           data: Dictionary containing the details of the event
        """
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            group,
            {
                "type": "notify",
                "event_name": event_name,
                "data": data,
            },
        )

    @staticmethod
    async def update_data(group: str, data: dict | None = None) -> None:
        """
        Sends data updates to public properties of all component that are subscribed to
        WebSocket connections in a group.

        Args:
           group: WebSocket group name to send the update to. This can be a normal
                group name or the predefined ones:
                * `user.{user_id}`
                * `session.{session_key}`
                * `broadcast`
           data: Dictionary containing the data to be sent to group members.
                IMPORTANT: All keys in this dict must match the components'
                public_properties names.
        """
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            group,
            {
                "type": "component.update_data",
                "group": group,
                "data": data or {},
            },
        )

    @staticmethod
    async def component_remove(group: str, component_id: str) -> None:
        """
        Send component removal notification to all WebSocket connections in a group.

        Args:
            group: WebSocket group name to send the removal notification to
            component_id: Unique identifier of the component to be removed
        """
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            group,
            {
                "type": "component.remove",
                "group": group,
                "component_id": component_id,
            },
        )

    @staticmethod
    async def subscription_response(
        group: str, status: str, message: str | None = None
    ) -> None:
        """
        Send subscription confirmation to a WebSocket group.

        Args:
            group: WebSocket group name
            status: "subscribed", "unsubscribed", or "error"
            message: Optional additional details
        """
        assert status in ["subscribed", "unsubscribed", "error"]
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            group,
            {
                "type": "subscription.response",
                "group": group,
                "status": status,  # "subscribed", "unsubscribed", "error"
                "message": message or "",
            },
        )
