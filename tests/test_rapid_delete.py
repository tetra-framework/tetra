import asyncio
import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from tetra.consumers import TetraConsumer
from tetra.utils import request_id
from apps.main.models import WatchableModel
from tetra.registry import channels_group_registry


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_rapid_deletions_sync():
    """Test that rapid deletion of multiple models correctly notifies other subscribed clients."""
    # Setup two clients
    session1 = SessionStore()
    session1.create()
    communicator1 = WebsocketCommunicator(TetraConsumer.as_asgi(), "/ws/tetra/")
    communicator1.scope.update(
        {"type": "websocket", "session": session1, "user": AnonymousUser()}
    )
    connected1, _ = await communicator1.connect()
    assert connected1

    session2 = SessionStore()
    session2.create()
    communicator2 = WebsocketCommunicator(TetraConsumer.as_asgi(), "/ws/tetra/")
    communicator2.scope.update(
        {"type": "websocket", "session": session2, "user": AnonymousUser()}
    )
    connected2, _ = await communicator2.connect()
    assert connected2

    try:
        # Create 10 models
        objs = []
        for i in range(10):
            objs.append(WatchableModel.objects.create(name=f"Item {i}"))

        # Both clients subscribe to all 10 items
        for obj in objs:
            group = f"main.watchablemodel.{obj.pk}"
            channels_group_registry.register(group)
            await communicator1.send_json_to({"type": "subscribe", "group": group})
            await communicator1.receive_json_from()
            await communicator2.send_json_to({"type": "subscribe", "group": group})
            await communicator2.receive_json_from()

        # Simulate Client 1 deleting 10 items rapidly
        # We'll use different request IDs for each
        for i, obj in enumerate(objs):
            req_id = f"req-{i}"
            request_id.set(req_id)
            try:
                obj.delete()
            finally:
                request_id.set(None)

        # Give it a bit of time
        await asyncio.sleep(0.5)

        # Check if Client 2 received all 10 removal messages
        received_groups = []
        for _ in range(10):
            try:
                msg = await communicator2.receive_json_from(timeout=1)
                assert msg["type"] == "component.removed"
                received_groups.append(msg["payload"]["group"])
            except asyncio.TimeoutError:
                break

        print(f"Received {len(received_groups)} removals on Client 2")
        assert len(received_groups) == 10

    finally:
        await communicator1.disconnect()
        await communicator2.disconnect()
