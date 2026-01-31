import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from django.test import RequestFactory
from tetra.views import component_method
from tetra.utils import request_id
from apps.main.models import WatchableModel


@pytest.mark.django_db
def test_request_id_tracking():
    # Setup: a ReactiveModel and a component method call
    obj = WatchableModel.objects.create(name="Original")

    # We need to mock a component to satisfy component_method's logic
    # But it's easier to mock at the level of the ReactiveModel's post_save handler call

    with patch(
        "tetra.dispatcher.ComponentDispatcher.update_data", new_callable=AsyncMock
    ) as mock_update_data:
        # 1. Test that without a request context, sender_id is None
        request_id.set(None)
        obj.name = "Changed 1"
        obj.save()

        # Check call
        assert mock_update_data.call_count == 1
        assert mock_update_data.call_args[1].get("sender_id") is None

        mock_update_data.reset_mock()

        # 2. Test that with a request context (simulated), sender_id is passed
        test_id = "test-request-id-123"
        request_id.set(test_id)

        obj.name = "Changed 2"
        obj.save()

        assert mock_update_data.call_count == 1
        assert mock_update_data.call_args[1].get("sender_id") == test_id


@pytest.mark.django_db
def test_request_id_extraction_in_view():
    factory = RequestFactory()
    test_id = "request-456"

    # Construct a payload that matches the tetra-1.0 protocol
    payload = {
        "protocol": "tetra-1.0",
        "id": test_id,
        "type": "call",
        "payload": {
            "component_id": "comp-1",
            "method": "some_method",
            "args": [],
            "state": {},
            "encrypted_state": None,
            "children_state": {},
        },
    }

    request = factory.post(
        "/tetra/call/main/main/MyComponent/some_method",
        data=json.dumps(payload),
        content_type="application/json",
    )
    request._dont_enforce_csrf_checks = True

    # We need to mock the Library and Component to let the view proceed
    with patch("tetra.views.Library") as mock_library:
        mock_component = MagicMock()
        mock_component._public_methods = [{"name": "some_method"}]
        mock_library.registry = {
            "main": {"main": MagicMock(components={"MyComponent": mock_component})}
        }

        # We also need to mock from_state to return something that has _call_public_method
        mock_inst = MagicMock()
        mock_component.from_state.return_value = mock_inst

        # Reset request_id
        request_id.set(None)

        from tetra.views import _component_method

        _component_method(request, "main", "main", "MyComponent", "some_method")

        # Check if request_id was set
        assert request_id.get() == test_id
