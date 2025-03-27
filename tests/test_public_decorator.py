from types import FunctionType, MethodType

from utils import extract_component_tag
from main.components.default import ComponentWithPublic
from tests.main.helpers import render_component_tag


def test_public_decorator_is_replaced_with_actual_method_or_attribute(request):
    # assert extract_component(content) == "mMessage"
    c = ComponentWithPublic(request)
    # make sure that @public decorated methods and attributes are replaced with their
    # actual method/attribute - they must not be "PublicMeta"
    assert type(c.msg) is str
    assert isinstance(c.do_something, MethodType)


def test_public_subscribe_renders_attrs(request_with_session):
    """Checks if a @public.subscribe decorator renders the attr correctly."""
    content = render_component_tag(
        request_with_session, "{% @ main.default.ComponentWithPublicSubscribe / %}"
    )
    component = extract_component_tag(content)
    assert component.has_attr("x-on:keyup.enter")
    assert component.attrs["x-on:keyup.enter"] == "do_something($event.detail)"
