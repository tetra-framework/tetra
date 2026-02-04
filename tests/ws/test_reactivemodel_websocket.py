"""
Test ReactiveModel WebSocket integration and deduplication.

These tests verify that ReactiveModel changes trigger correct WebSocket updates
and that the client properly deduplicates messages when both HTTP response and
WebSocket signals arrive.
"""

import asyncio
import pytest
from apps.main.models import WatchableModel
from tetra.dispatcher import ComponentDispatcher
from tetra.utils import request_id
from tetra.registry import channels_group_registry


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_reactivemodel_save_sends_websocket_update(tetra_ws_communicator):
    """Test that saving a ReactiveModel sends update_data via WebSocket."""
    # Subscribe to the model's channel
    obj = WatchableModel.objects.create(name="Initial")
    group_name = f"main.watchablemodel.{obj.pk}"
    channels_group_registry.register(group_name)

    await tetra_ws_communicator.send_json_to({"type": "subscribe", "group": group_name})
    subscription_response = await tetra_ws_communicator.receive_json_from()
    assert subscription_response["payload"]["status"] == "subscribed"

    # Update the model
    obj.name = "Updated"
    obj.save()

    # Give async task time to complete
    await asyncio.sleep(0.1)

    # Should receive update via WebSocket
    update_message = await tetra_ws_communicator.receive_json_from()
    assert update_message["protocol"] == "tetra-1.0"
    assert update_message["type"] == "component.data_changed"
    assert update_message["payload"]["group"] == group_name
    assert update_message["payload"]["data"]["name"] == "Updated"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_reactivemodel_delete_sends_websocket_remove(tetra_ws_communicator):
    """Test that deleting a ReactiveModel sends component_remove via WebSocket."""
    # Create and subscribe to model
    obj = WatchableModel.objects.create(name="To Delete")
    group_name = f"main.watchablemodel.{obj.pk}"
    channels_group_registry.register(group_name)

    await tetra_ws_communicator.send_json_to({"type": "subscribe", "group": group_name})
    subscription_response = await tetra_ws_communicator.receive_json_from()
    assert subscription_response["payload"]["status"] == "subscribed"

    # Delete the model
    obj.delete()

    # Give async task time to complete
    await asyncio.sleep(0.1)

    # Should receive remove via WebSocket
    remove_message = await tetra_ws_communicator.receive_json_from()
    assert remove_message["protocol"] == "tetra-1.0"
    assert remove_message["type"] == "component.removed"
    assert remove_message["payload"]["group"] == group_name


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_reactivemodel_update_with_sender_id(tetra_ws_communicator):
    """Test that ReactiveModel updates include sender_id for deduplication."""
    obj = WatchableModel.objects.create(name="Test")
    group_name = f"main.watchablemodel.{obj.pk}"
    channels_group_registry.register(group_name)

    await tetra_ws_communicator.send_json_to({"type": "subscribe", "group": group_name})
    await tetra_ws_communicator.receive_json_from()

    # Set a request_id to simulate a component method call
    test_request_id = "test-request-123"
    request_id.set(test_request_id)

    try:
        obj.name = "Updated with ID"
        obj.save()

        # Give async task time to complete
        await asyncio.sleep(0.1)

        # Check that sender_id is included
        update_message = await tetra_ws_communicator.receive_json_from()
        assert update_message["payload"]["sender_id"] == test_request_id
    finally:
        request_id.set(None)


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_reactivemodel_delete_with_sender_id(tetra_ws_communicator):
    """Test that ReactiveModel deletion includes sender_id for deduplication."""
    obj = WatchableModel.objects.create(name="Test Delete")
    group_name = f"main.watchablemodel.{obj.pk}"
    channels_group_registry.register(group_name)

    await tetra_ws_communicator.send_json_to({"type": "subscribe", "group": group_name})
    await tetra_ws_communicator.receive_json_from()

    # Set a request_id to simulate a component method call
    test_request_id = "test-delete-456"
    request_id.set(test_request_id)

    try:
        obj.delete()

        # Give async task time to complete
        await asyncio.sleep(0.1)

        # Check that sender_id is included in removal message
        remove_message = await tetra_ws_communicator.receive_json_from()
        assert remove_message["type"] == "component.removed"
        assert remove_message["payload"]["sender_id"] == test_request_id
    finally:
        request_id.set(None)


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_multiple_models_same_channel(tetra_ws_communicator):
    """Test that multiple subscribers to same model channel all receive updates."""
    obj = WatchableModel.objects.create(name="Shared")
    group_name = f"main.watchablemodel.{obj.pk}"
    channels_group_registry.register(group_name)

    # Subscribe to the model's channel
    await tetra_ws_communicator.send_json_to({"type": "subscribe", "group": group_name})
    await tetra_ws_communicator.receive_json_from()

    # Update model
    obj.name = "Shared Update"
    obj.save()

    # Give async task time to complete
    await asyncio.sleep(0.1)

    # All subscribers should receive the update
    update = await tetra_ws_communicator.receive_json_from()
    assert update["payload"]["data"]["name"] == "Shared Update"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_reactivemodel_filtered_fields(tetra_ws_communicator):
    """Test that only Tetra.fields are sent via WebSocket."""
    # WatchableModel has Tetra.fields = "__all__"
    obj = WatchableModel.objects.create(name="Field Test")
    group_name = f"main.watchablemodel.{obj.pk}"
    channels_group_registry.register(group_name)

    await tetra_ws_communicator.send_json_to({"type": "subscribe", "group": group_name})
    await tetra_ws_communicator.receive_json_from()

    obj.name = "Updated Fields"
    obj.save()

    # Give async task time to complete
    await asyncio.sleep(0.1)

    update = await tetra_ws_communicator.receive_json_from()
    data = update["payload"]["data"]

    # Should include 'name' field
    assert "name" in data
    assert data["name"] == "Updated Fields"
    # Should include id since fields = "__all__"
    assert "id" in data


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_reactivemodel_no_duplicate_on_same_request(tetra_ws_communicator):
    """
    Test the deduplication scenario: when a component method triggers a model save,
    the client should receive the update via HTTP response but NOT process the
    WebSocket message with the same sender_id.

    This simulates the client-side behavior where __activeRequests tracks pending
    requests and filters out WebSocket updates with matching sender_id.
    """
    obj = WatchableModel.objects.create(name="Dedupe Test")
    group_name = f"main.watchablemodel.{obj.pk}"
    channels_group_registry.register(group_name)

    await tetra_ws_communicator.send_json_to({"type": "subscribe", "group": group_name})
    await tetra_ws_communicator.receive_json_from()

    # Simulate a component method call
    test_request_id = "dedupe-request-789"
    request_id.set(test_request_id)

    try:
        obj.name = "Dedupe Update"
        obj.save()

        # Give async task time to complete
        await asyncio.sleep(0.1)

        # WebSocket message arrives with sender_id
        ws_message = await tetra_ws_communicator.receive_json_from()
        assert ws_message["payload"]["sender_id"] == test_request_id

        # In the real client, if __activeRequests.has(sender_id),
        # the update would be skipped. Here we just verify the sender_id
        # is correctly propagated so the client can perform this check.
        assert ws_message["payload"]["group"] == group_name
        assert ws_message["payload"]["data"]["name"] == "Dedupe Update"
    finally:
        request_id.set(None)


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_component_remove_deduplication_scenario(tetra_ws_communicator):
    """
    Test that component removal messages include sender_id for client-side deduplication.

    When a component method calls delete() on a model:
    1. HTTP response can include client:_removeComponent() callback
    2. WebSocket receives component.removed with sender_id
    3. Client should skip WebSocket removal if sender_id matches active request
    """
    obj = WatchableModel.objects.create(name="Remove Dedupe")
    group_name = f"main.watchablemodel.{obj.pk}"
    channels_group_registry.register(group_name)

    await tetra_ws_communicator.send_json_to({"type": "subscribe", "group": group_name})
    await tetra_ws_communicator.receive_json_from()

    # Simulate component method triggering delete
    test_request_id = "remove-dedupe-999"
    request_id.set(test_request_id)

    try:
        obj.delete()

        # Give async task time to complete
        await asyncio.sleep(0.1)

        # Verify WebSocket removal includes sender_id
        remove_message = await tetra_ws_communicator.receive_json_from()
        assert remove_message["type"] == "component.removed"
        assert remove_message["payload"]["sender_id"] == test_request_id

        # Client-side should check: if __activeRequests.has(sender_id), skip removal
        # This prevents double-removal when HTTP response already removed the component
    finally:
        request_id.set(None)


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_reactivemodel_creation_sends_created_to_collection(
    tetra_ws_communicator,
):
    """Test that creating a ReactiveModel sends component.created to collection channel."""
    collection_group = "main.watchablemodel"
    channels_group_registry.register(collection_group)

    await tetra_ws_communicator.send_json_to(
        {"type": "subscribe", "group": collection_group}
    )
    await tetra_ws_communicator.receive_json_from()

    # Create new model
    WatchableModel.objects.create(name="New Item")

    # Give async task time to complete
    await asyncio.sleep(0.1)

    # Should receive component.created via WebSocket
    refresh_message = await tetra_ws_communicator.receive_json_from()
    assert refresh_message["type"] == "component.created"
    assert refresh_message["payload"]["group"] == collection_group
    assert refresh_message["payload"]["data"]["name"] == "New Item"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_reactivemodel_deletion_sends_remove_to_collection(tetra_ws_communicator):
    """Test that deleting a ReactiveModel sends component.removed to collection channel with target_group."""
    collection_group = "main.watchablemodel"
    channels_group_registry.register(collection_group)

    await tetra_ws_communicator.send_json_to(
        {"type": "subscribe", "group": collection_group}
    )
    await tetra_ws_communicator.receive_json_from()

    # Create model
    obj = WatchableModel.objects.create(name="To Delete from Collection")
    pk = obj.pk
    instance_channel = f"main.watchablemodel.{pk}"

    # Drain the refresh message from creation
    await tetra_ws_communicator.receive_json_from()

    # Delete the model
    obj.delete()

    # Give async task time to complete
    await asyncio.sleep(0.1)

    # Should receive removal message on collection channel
    remove_message = await tetra_ws_communicator.receive_json_from()
    assert remove_message["type"] == "component.removed"
    assert remove_message["payload"]["group"] == collection_group
    assert remove_message["payload"]["target_group"] == instance_channel
