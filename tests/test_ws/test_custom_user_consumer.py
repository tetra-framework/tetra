import pytest
from django.test import override_settings
from django.contrib.auth import get_user_model
from tetra.consumers import TetraConsumer
from tetra.dispatcher import ComponentDispatcher


@pytest.mark.django_db
@pytest.mark.asyncio
# Since we cannot easily switch AUTH_USER_MODEL per test in async context with get_user_model()
# being called early, this test is meant to be run with AUTH_USER_MODEL="another_app.CustomUser"
# configured in settings.
async def test_custom_user_auto_subscription(tetra_ws_communicator):
    """Test that consumer auto-subscribes to custom user group."""
    user_model = get_user_model()
    assert user_model.__name__ == "CustomUser"
    assert user_model._meta.app_label == "another_app"

    communicator = tetra_ws_communicator
    user = communicator.scope["user"]
    assert user.is_authenticated
    assert isinstance(user, user_model)

    user_prefix = "another_app.customuser"
    expected_group = f"{user_prefix}.{user.id}"

    # Test auto-subscription by sending a message to the custom user group
    await ComponentDispatcher.subscription_response(
        expected_group, status="subscribed", message="test custom user"
    )

    response = await communicator.receive_json_from()
    assert response["protocol"] == "tetra-1.0"
    assert response["type"] == "subscription.response"
    assert response["payload"]["group"] == expected_group


@pytest.mark.django_db
@pytest.mark.asyncio
# Since we cannot easily switch AUTH_USER_MODEL per test in async context with get_user_model()
# being called early, this test is meant to be run with AUTH_USER_MODEL="another_app.CustomUser"
# configured in settings.
async def test_custom_user_manual_subscription_validation(tetra_ws_communicator):
    """Test manual subscription validation with custom user model."""
    communicator = tetra_ws_communicator
    user = communicator.scope["user"]
    user_prefix = "another_app.customuser"

    # Own group should be allowed (it's already auto-subscribed, but let's try manual)
    own_group = f"{user_prefix}.{user.id}"
    await communicator.send_json_to({"type": "subscribe", "group": own_group})
    response = await communicator.receive_json_from()
    assert response["payload"]["status"] in ["subscribed", "resubscribed"]

    # Other user's group should be blocked
    other_group = f"{user_prefix}.999"
    await communicator.send_json_to({"type": "subscribe", "group": other_group})
    response = await communicator.receive_json_from()
    assert response["payload"]["status"] == "error"
    assert response["payload"]["message"] == "Unauthorized"

    # Old hardcoded "user." prefix should be treated as a normal group now
    old_group = "user.1"
    await communicator.send_json_to({"type": "subscribe", "group": old_group})
    response = await communicator.receive_json_from()
    assert response["payload"]["status"] == "subscribed"
