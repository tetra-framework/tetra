import pytest
from typing import Optional
from pydantic import ValidationError
from django.test import RequestFactory
from tetra import Library, public
from tetra.components.base import Component
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser

my_lib = Library("test_pydantic", "main")


def get_request_with_session():
    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


@my_lib.register
class TypedComponent(Component):
    int_attr: int = public(10)
    str_attr: str = public("hello")
    bool_attr: bool = public(True)
    list_attr: list[int] = public([1, 2, 3])

    template = "<div></div>"


@pytest.mark.django_db
def test_pydantic_validation_success():
    request = get_request_with_session()

    comp = TypedComponent(request)
    # Valid values
    comp.int_attr = 20
    comp.str_attr = "world"
    comp.bool_attr = False
    comp.list_attr = [4, 5]

    # Should NOT raise ValidationError
    comp._encoded_state()


@pytest.mark.django_db
def test_pydantic_validation_none_not_allowed_on_strict_type():
    request = get_request_with_session()

    comp = TypedComponent(request)
    # int_attr is hinted as int, so None should NOT be allowed after this fix
    comp.int_attr = None

    with pytest.raises(ValidationError):
        comp._encoded_state()


@my_lib.register
class OptionalComponent(Component):
    opt_int: Optional[int] = public(None)
    template = "<div></div>"


@pytest.mark.django_db
def test_pydantic_validation_none_allowed_on_optional():
    request = get_request_with_session()

    comp = OptionalComponent(request)
    comp.opt_int = None
    # Should NOT raise ValidationError
    comp._encoded_state()


@pytest.mark.django_db
def test_pydantic_validation_error_int():
    request = get_request_with_session()

    comp = TypedComponent(request)
    comp.int_attr = "not an int"

    with pytest.raises(ValidationError) as excinfo:
        comp._encoded_state()

    assert "int_attr" in str(excinfo.value)
    assert "Input should be a valid integer" in str(excinfo.value)


@pytest.mark.django_db
def test_pydantic_validation_error_list():
    request = get_request_with_session()

    comp = TypedComponent(request)
    comp.list_attr = [1, "not an int", 3]

    with pytest.raises(ValidationError) as excinfo:
        comp._encoded_state()

    assert "list_attr" in str(excinfo.value)


@pytest.mark.django_db
def test_pydantic_validation_coercion():
    request = get_request_with_session()

    comp = TypedComponent(request)
    # Pydantic by default coerces types if possible (e.g. "123" to 123)
    comp.int_attr = "123"

    # Should NOT raise ValidationError because it's coerced
    comp._encoded_state()
    # Note: the attribute itself is still "123" on the component because we don't
    # write back the validated data to the component in _encoded_state
    assert comp.int_attr == "123"


@my_lib.register
class InheritanceComponent(TypedComponent):
    new_attr: float = public(1.5)


@pytest.mark.django_db
def test_pydantic_validation_inheritance():
    request = get_request_with_session()

    comp = InheritanceComponent(request)
    comp.int_attr = "invalid"

    with pytest.raises(ValidationError) as excinfo:
        comp._encoded_state()
    assert "int_attr" in str(excinfo.value)

    comp.int_attr = 10
    comp.new_attr = "invalid float"
    with pytest.raises(ValidationError) as excinfo:
        comp._encoded_state()
    assert "new_attr" in str(excinfo.value)
