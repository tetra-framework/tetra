import asyncio
import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from tetra.consumers import TetraConsumer
from tetra.dispatcher import ComponentDispatcher
from tetra.utils import request_id
from apps.main.models import WatchableModel
from tetra.registry import channels_group_registry


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_rapid_signals_dispatch():
    """Verify that multiple model signals are correctly dispatched as removal messages to the client."""
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
        # Create 10 items
        objs = []
        pks = []
        for i in range(10):
            obj = WatchableModel.objects.create(name=f"Item {i}")
            objs.append(obj)
            pks.append(obj.pk)

        # Subscribe to all 10
        for pk in pks:
            group = f"main.watchablemodel.{pk}"
            channels_group_registry.register(group)
            await communicator.send_json_to({"type": "subscribe", "group": group})
            await communicator.receive_json_from()

        # Delete all 10 in a loop
        for i, obj in enumerate(objs):
            req_id = f"req-{i}"
            request_id.set(req_id)
            try:
                obj.delete()
            finally:
                request_id.set(None)

        # Receive all 10
        received_groups = []
        for _ in range(10):
            try:
                msg = await communicator.receive_json_from(timeout=1)
                assert msg["type"] == "component.removed"
                received_groups.append(msg["payload"]["group"])
            except asyncio.TimeoutError:
                break

        print(f"Received {len(received_groups)} removals")
        for pk in pks:
            expected_group = f"main.watchablemodel.{pk}"
            assert expected_group in received_groups

    finally:
        await communicator.disconnect()
