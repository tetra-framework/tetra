from asyncio import sleep

import pytest
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
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == "broadcast"

    # Test session group
    await ComponentDispatcher.subscription_response(
        f"session.{session_key}", status="subscribed", message="test session"
    )
    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == f"session.{session_key}"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_subscribe(tetra_ws_communicator):
    communicator = tetra_ws_communicator
    # Subscribe to a group
    group_name = "test-group"
    await communicator.send_json_to({"type": "subscribe", "group": group_name})

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == group_name
    assert response["payload"]["status"] == "subscribed"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_subscribe_unsubscribe(tetra_ws_communicator):
    """Test manual subscription and unsubscription."""
    communicator = tetra_ws_communicator
    group_name = "test-group"

    # Subscribe
    await communicator.send_json_to({"type": "subscribe", "group": group_name})
    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == group_name
    assert response["payload"]["status"] == "subscribed"

    # Unsubscribe
    await communicator.send_json_to({"type": "unsubscribe", "group": group_name})
    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == group_name
    assert response["payload"]["status"] == "unsubscribed"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_resubscribed(tetra_ws_communicator):
    """Test that a user can't subscribe to a group they're already subscribed to."""
    communicator = tetra_ws_communicator
    group_name = "test-group"

    # Subscribe
    await communicator.send_json_to({"type": "subscribe", "group": group_name})
    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == group_name
    assert response["payload"]["status"] == "subscribed"

    # Subscribe to same group again
    await communicator.send_json_to({"type": "subscribe", "group": group_name})
    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == group_name
    assert response["payload"]["status"] == "resubscribed"


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
    await ComponentDispatcher.data_changed(group_name, {"title": "New Title"})

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "component.data_changed"
    assert response["payload"]["group"] == group_name
    assert response["payload"]["data"] == {"title": "New Title"}

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
    await ComponentDispatcher.component_removed(group_name, "comp_123")

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "component.removed"
    assert response["payload"]["group"] == group_name
    assert response["payload"]["component_id"] == "comp_123"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_component_remove_with_target_group_handler(tetra_ws_communicator):
    """Test the component_remove event handler with target_group."""
    communicator = tetra_ws_communicator

    group_name = "remove-group"
    # Subscribe
    await communicator.send_json_to({"type": "subscribe", "group": group_name})
    await communicator.receive_json_from()

    # Trigger component_remove via dispatcher with target_group
    await ComponentDispatcher.component_removed(
        group_name, target_group="target-item-group"
    )

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "component.removed"
    assert response["payload"]["group"] == group_name
    assert response["payload"]["target_group"] == "target-item-group"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_component_add_handler(tetra_ws_communicator):
    """Test the component_add event handler."""
    communicator = tetra_ws_communicator
    component_id = "new-component-id-124"
    group_name = "add-group"
    target_group = "target-item-group"
    # Subscribe
    await communicator.send_json_to({"type": "subscribe", "group": group_name})
    await communicator.receive_json_from()

    # Trigger component_add via dispatcher
    await ComponentDispatcher.component_created(
        group_name, component_id=component_id, target_group=target_group
    )

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "component.created"
    assert response["payload"]["group"] == group_name
    assert response["payload"]["target_group"] == target_group
    assert response["payload"]["component_id"] == component_id


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
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "notify"
    assert response["payload"]["event_name"] == "tetra:test-event"
    assert response["payload"]["data"] == {"foo": "bar"}


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handle_subscribe_missing_group(tetra_ws_communicator):
    communicator = tetra_ws_communicator

    await communicator.send_json_to({"type": "subscribe", "group": None})

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] is None
    assert response["payload"]["status"] == "error"
    assert response["payload"]["message"] == "Invalid group name"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handle_subscribe_unauthorized_group(tetra_ws_communicator):
    communicator = tetra_ws_communicator
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    user_prefix = f"{user_model._meta.app_label}.{user_model._meta.model_name}"

    unauthorized_group = f"{user_prefix}.999"  # Assuming our user ID is not 999
    await communicator.send_json_to({"type": "subscribe", "group": unauthorized_group})

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == unauthorized_group
    assert response["payload"]["status"] == "error"
    assert response["payload"]["message"] == "Unauthorized"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handle_subscribe_old_user_prefix_fails(tetra_ws_communicator):
    """Test that the old hardcoded 'user.' prefix is no longer treated as a user group (or at least doesn't pass the unauthorized check if it's not the real prefix)."""
    communicator = tetra_ws_communicator

    # If the real prefix is e.g. 'auth.user', then 'user.1' should just be treated as a normal group
    # or fail if it's not registered. Currently we don't have a registry check fully implemented.
    # But it definitely shouldn't be caught by the user_prefix check.

    group_name = "user.1"
    await communicator.send_json_to({"type": "subscribe", "group": group_name})

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == group_name
    # Since it's not a user group anymore, it should just succeed subscribing as a normal group
    # (unless there's other validation)
    assert response["payload"]["status"] == "subscribed"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handle_subscribe_any_session_group(tetra_ws_communicator):
    communicator = tetra_ws_communicator

    unauthorized_group = "session.no-way-that-this-session-id-is-valid"
    await communicator.send_json_to({"type": "subscribe", "group": unauthorized_group})

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == unauthorized_group
    assert response["payload"]["status"] == "error"
    assert (
        response["payload"]["message"]
        == "No manually joining of session groups allowed."
    )


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handle_subscribe_own_session_group(tetra_ws_communicator):
    """Test subscribing manually to the valid, own session group must fail."""

    own_session_group = f"session.{tetra_ws_communicator.scope['session'].session_key}"
    await tetra_ws_communicator.send_json_to(
        {"type": "subscribe", "group": own_session_group}
    )

    response = await tetra_ws_communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == own_session_group
    assert response["payload"]["status"] == "error"
    assert (
        response["payload"]["message"]
        == "No manually joining of session groups allowed."
    )
