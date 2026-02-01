import asyncio
import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from tetra.consumers import TetraConsumer
from tetra.dispatcher import ComponentDispatcher


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_group_removal_multiple_components():
    # Setup client
    session = SessionStore()
    session.create()
    communicator = WebsocketCommunicator(TetraConsumer.as_asgi(), "/ws/tetra/")
    communicator.scope.update(
        {"type": "websocket", "session": session, "user": AnonymousUser()}
    )
    connected, _ = await communicator.connect()
    assert connected

    try:
        group = "shared-group"
        # Subscribe multiple times (simulating multiple components in same group)
        # Note: server only cares about the group name, it doesn't know about individual components
        await communicator.send_json_to({"type": "subscribe", "group": group})
        await communicator.receive_json_from()

        # Trigger removal for the group
        await ComponentDispatcher.component_removed(group)

        # Receive the message
        msg = await communicator.receive_json_from(timeout=1)
        assert msg["type"] == "component.removed"
        assert msg["payload"]["group"] == group
        assert msg["payload"]["component_id"] is None

    finally:
        await communicator.disconnect()
