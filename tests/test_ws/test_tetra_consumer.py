from asyncio import sleep

import pytest
from channels.testing import WebsocketCommunicator
from tetra.consumers import TetraConsumer
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from tetra.dispatcher import ComponentDispatcher


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_connect(tetra_ws_communicator):
    """Test successful connection with session."""
    # we don't have to do anything here, as the consumer connection is asserted
    # correctly within the fixture
    pass


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_consumer_connection(tetra_ws_communicator):
    communicator = tetra_ws_communicator
    # Subscribe to a group
    await communicator.send_json_to({"type": "subscribe", "group": "test-group"})

    response = await communicator.receive_json_from()
    assert response["type"] == "subscription.response"
    assert response["group"] == "test-group"
    assert response["status"] == "subscribed"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_consumer_connection_with_no_session():
    """Test connection is closed if session is missing."""

    # we can't use the tetra_ws_communicator fixture here, as it would return a
    # communicator (to the TetraConsumer) with a valid session scope
    from tetra.consumers import TetraConsumer
    from channels.testing import WebsocketCommunicator

    communicator = WebsocketCommunicator(
        TetraConsumer.as_asgi(),
        "/ws/tetra/",
    )
    if "session" in communicator.scope:
        del communicator.scope["session"]

    connected, _ = await communicator.connect()
    assert not connected
    await communicator.disconnect()


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_auto_subscriptions(tetra_ws_communicator):
    """Test that consumer auto-subscribes to session and broadcast groups."""
    communicator = tetra_ws_communicator
    session_key = communicator.scope["session"].session_key

    # Check subscribed groups internally if possible,
    # or test by sending messages to those groups.
    # TetraConsumer stores them in self.subscribed_groups

    # Since we can't easily access the consumer instance from WebsocketCommunicator
    # (it's wrapped), we test by sending messages to the groups.

    # Test broadcast group
    await ComponentDispatcher.subscription_response(
        "broadcast", status="subscribed", message="test broadcast"
    )
    response = await communicator.receive_json_from()
    assert response["type"] == "subscription.response"
    assert response["group"] == "broadcast"

    # Test session group
    await ComponentDispatcher.subscription_response(
        f"session.{session_key}", status="subscribed", message="test session"
    )
    response = await communicator.receive_json_from()
    assert response["type"] == "subscription.response"
    assert response["group"] == f"session.{session_key}"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_subscribe_unsubscribe(tetra_ws_communicator):
    """Test manual subscription and unsubscription."""
    communicator = tetra_ws_communicator

    # Subscribe
    await communicator.send_json_to({"type": "subscribe", "group": "custom-group"})
    response = await communicator.receive_json_from()
    assert response["type"] == "subscription.response"
    assert response["group"] == "custom-group"
    assert response["status"] == "subscribed"

    # Unsubscribe
    await communicator.send_json_to({"type": "unsubscribe", "group": "custom-group"})
    response = await communicator.receive_json_from()
    assert response["type"] == "subscription.response"
    assert response["group"] == "custom-group"
    assert response["status"] == "unsubscribed"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_component_update_data_handler(tetra_ws_communicator):
    """Test the component_update_data event handler."""
    from tetra.components import subscription, Component, public
    from tetra.library import Library
    from django.test import RequestFactory

    session = tetra_ws_communicator.scope["session"]

    # Mock a component and register it
    lib = Library("test_lib", app="main")

    @lib.register
    class MockComponent(Component):
        title = public("Original Title")
        template = "<div>{{ title }}</div>"

    # Manually add to registry for testing
    group_name = "test-group"

    request = RequestFactory().get("/")
    request.session = session
    component_inst = MockComponent(_request=request)
    subscription.registry[group_name] = [component_inst]

    communicator = tetra_ws_communicator
    # Subscribe to the group
    await communicator.send_json_to({"type": "subscribe", "group": group_name})
    await communicator.receive_json_from()

    # Trigger component_update_data via dispatcher
    await ComponentDispatcher.update_data(group_name, {"title": "New Title"})

    response = await communicator.receive_json_from()
    assert response["type"] == "component.update_data"
    assert response["group"] == group_name
    assert response["data"] == {"title": "New Title"}

    # Clean up registry
    del subscription.registry[group_name]


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_component_remove_handler(tetra_ws_communicator):
    """Test the component_remove event handler."""
    communicator = tetra_ws_communicator

    group_name = "remove-group"
    # Subscribe
    await communicator.send_json_to({"type": "subscribe", "group": group_name})
    await communicator.receive_json_from()

    # Trigger component_remove via dispatcher
    await ComponentDispatcher.component_remove(group_name, "comp_123")

    response = await communicator.receive_json_from()
    assert response["type"] == "component.remove"
    assert response["group"] == group_name
    assert response["component_id"] == "comp_123"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_notify_handler(tetra_ws_communicator):
    """Test the notify event handler."""
    communicator = tetra_ws_communicator

    group_name = "notify-group"
    # Subscribe
    await communicator.send_json_to({"type": "subscribe", "group": group_name})
    await communicator.receive_json_from()

    # Trigger notify via dispatcher
    from tetra.dispatcher import ComponentDispatcher

    await ComponentDispatcher.notify(group_name, "tetra:test-event", {"foo": "bar"})

    response = await communicator.receive_json_from()
    assert response["type"] == "notify"
    assert response["event_name"] == "tetra:test-event"
    assert response["data"] == {"foo": "bar"}
