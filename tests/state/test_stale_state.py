"""Tests for stale component state handling.

When a component's state references database objects that have been deleted
by another client, the framework should return a graceful error response
instead of crashing with a 500 error.
"""

import json
import pytest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser

from tetra import Library
from tetra.components import Component, public
from tetra.state import encode_component
from tetra.views import _component_method
from tetra.exceptions import StaleComponentStateError
from apps.main.models import SimpleModel

lib = Library("stale_test", "main")


@lib.register
class ItemComponent(Component):
    """Test component that references a database object."""

    template = "<div>{{ item.name }}</div>"

    def load(self, item_id):
        # This will fail with DoesNotExist if item was deleted
        self.item = SimpleModel.objects.get(pk=item_id)

    @public
    def update_item(self):
        """Dummy method to test calling methods on stale components."""
        self.item.name = "Updated"
        self.item.save()


def get_request_with_session():
    """Helper to create a request with session."""
    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


@pytest.mark.django_db
def test_stale_state_raises_exception():
    """Test that from_state raises StaleComponentStateError when object doesn't exist."""
    request = get_request_with_session()

    # Create an item and a component
    item = SimpleModel.objects.create(name="Test Item")
    comp = ItemComponent(request, key="test-key", item_id=item.pk)

    # Encode the state
    encoded_state = encode_component(comp)

    # Delete the item
    item.delete()

    # Try to restore component - should raise StaleComponentStateError
    state_dict = {"encrypted": encoded_state, "data": {"key": "test-key"}}

    with pytest.raises(StaleComponentStateError) as exc_info:
        ItemComponent.from_state(state_dict, request)

    assert "stale" in str(exc_info.value).lower()
    assert "ItemComponent" in str(exc_info.value)


@pytest.mark.django_db
def test_stale_state_view_returns_410():
    """Test that the view returns 410 Gone when component state is stale."""
    request = get_request_with_session()

    # Create an item and a component
    item = SimpleModel.objects.create(name="Test Item")
    comp = ItemComponent(request, key="test-key", item_id=item.pk)

    # Encode the state
    encoded_state = encode_component(comp)

    # Delete the item (simulating another client deleting it)
    item.delete()

    # Prepare request to call component method
    factory = RequestFactory()
    component_state = {
        "protocol": "tetra-1.0",
        "id": "test-request-id",
        "type": "call",
        "payload": {
            "encrypted_state": encoded_state,
            "state": {"key": "test-key"},
            "children_state": [],
            "args": [],
            "method": "update_item",
            # Add component location metadata
            "app_name": "main",
            "library_name": "stale_test",
            "component_name": "item_component",
        },
    }

    post_request = factory.post(
        "/tetra/call/",
        json.dumps(component_state),
        content_type="application/json",
    )
    post_request.session = request.session
    post_request.user = AnonymousUser()
    post_request.csrf_processing_done = True

    # Call the view
    response = _component_method(post_request)

    # Should return 410 Gone
    assert response.status_code == 410

    # Check response content
    response_data = json.loads(response.content)
    assert response_data["success"] is False
    assert response_data["error"]["code"] == "StaleComponentState"
    assert "no longer valid" in response_data["error"]["message"]


@pytest.mark.django_db
def test_normal_operation_still_works():
    """Test that normal component operations still work correctly."""
    request = get_request_with_session()

    # Create an item and a component
    item = SimpleModel.objects.create(name="Test Item")
    comp = ItemComponent(request, key="test-key", item_id=item.pk)

    # Encode the state
    encoded_state = encode_component(comp)

    # DON'T delete the item - this should work normally

    # Restore component - should work fine
    state_dict = {"encrypted": encoded_state, "data": {"key": "test-key"}}
    restored_comp = ItemComponent.from_state(state_dict, request)

    assert restored_comp.item.pk == item.pk
    assert restored_comp.item.name == "Test Item"
