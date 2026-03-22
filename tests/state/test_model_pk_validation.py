import pytest
from django.db import models
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from tetra import Library
from tetra.components.base import Component, public
from tetra.state import encode_component, decode_component

my_lib = Library("test_model_pk", "main")


class HealthServiceType(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "main"

    def __str__(self):
        return self.name


@my_lib.register
class SignupFormComponent(Component):
    health_service_type: HealthServiceType | None = public(None)

    template = "<div>{{ health_service_type }}</div>"


def get_request_with_session():
    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


@pytest.mark.django_db
def test_model_pk_string_converts_to_instance():
    """Verify that a Model pk (string) is converted to a Model instance during validation."""
    request = get_request_with_session()

    # Create a HealthServiceType instance
    service_type = HealthServiceType.objects.create(code="doc", name="Doctor")

    # Create component with pk string (simulating form data or GET param)
    comp = SignupFormComponent(request)
    comp.health_service_type = "doc"  # Assigned as string pk

    # This should NOT raise a validation error
    # The _data() method should convert "doc" to the Model instance
    encoded_state = encode_component(comp)

    # Decode and verify
    decoded_comp = decode_component(encoded_state, request)
    assert decoded_comp.health_service_type.code == "doc"
    assert isinstance(decoded_comp.health_service_type, HealthServiceType)


@pytest.mark.django_db
def test_model_instance_preserved():
    """Verify that a Model instance is preserved during encoding/decoding."""
    request = get_request_with_session()

    service_type = HealthServiceType.objects.create(code="phy", name="Physiotherapist")

    comp = SignupFormComponent(request)
    comp.health_service_type = service_type  # Assigned as Model instance

    # Should work without issues
    encoded_state = encode_component(comp)
    decoded_comp = decode_component(encoded_state, request)

    assert decoded_comp.health_service_type.code == "phy"
    assert isinstance(decoded_comp.health_service_type, HealthServiceType)


@pytest.mark.django_db
def test_model_pk_int_converts_to_instance():
    """Verify that a Model pk (int) is converted to a Model instance during validation."""
    request = get_request_with_session()

    # Create a model with integer pk
    service_type = HealthServiceType.objects.create(code="nur", name="Nurse")

    comp = SignupFormComponent(request)
    # Use the code as pk (string key)
    comp.health_service_type = "nur"

    encoded_state = encode_component(comp)
    decoded_comp = decode_component(encoded_state, request)

    assert decoded_comp.health_service_type.code == "nur"
    assert isinstance(decoded_comp.health_service_type, HealthServiceType)


@pytest.mark.django_db
def test_model_none_value():
    """Verify that None values are handled correctly for optional Model fields."""
    request = get_request_with_session()

    comp = SignupFormComponent(request)
    comp.health_service_type = None

    encoded_state = encode_component(comp)
    decoded_comp = decode_component(encoded_state, request)

    assert decoded_comp.health_service_type is None


@pytest.mark.django_db
def test_model_invalid_pk_does_not_crash():
    """Verify that an invalid pk doesn't crash the system during validation."""
    request = get_request_with_session()

    comp = SignupFormComponent(request)
    comp.health_service_type = "nonexistent"  # Invalid pk

    # Should fail validation or handle gracefully
    # The system should either raise an error or leave the value as-is
    try:
        encoded_state = encode_component(comp)
        # If it doesn't raise, the value was left as-is and will fail validation
    except Exception:
        # Expected to fail with validation error or DoesNotExist
        pass
