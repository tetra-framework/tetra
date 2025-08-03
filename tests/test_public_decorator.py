from types import FunctionType, MethodType

import pytest

from tetra import public, Library, Component
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


default = Library("default", "main")


def test_subscribe_with_wrong_arguments():
    with pytest.raises(ValueError):

        @default.register
        class ComponentWithPublicSubscribe(Component):
            @public.subscribe("keyup.enter")
            def do_something(self) -> str:  # should have event_detail as param
                pass

            template = """<div id='component' {% ... attrs %}></div>"""


@default.register
class ComponentWithPublicSubscribe(Component):

    @public.subscribe("keyup.enter")
    def do_something(self, event_detail) -> str:
        pass

    template = """<div id='component' {% ... attrs %}></div>"""


def test_public_subscribe_renders_attrs(request_with_session):
    """Checks if a @public.subscribe decorator renders the attr correctly."""
    content = render_component_tag(
        request_with_session, "{% ComponentWithPublicSubscribe / %}"
    )
    component = extract_component_tag(content)
    assert component.has_attr("@keyup.enter")
    assert component.attrs["@keyup.enter"] == "do_something($event.detail)"


# ------------- watch -------------


class ComponentWatchBase(Component):
    template = """<div id='component' {% ... attrs %}></div>"""


def test_watch_parameter_count0():

    with pytest.raises(ValueError) as exc_info:

        @default.register
        class ComponentWatch1(ComponentWatchBase):
            @public.watch()
            def watchmethod(self, value, old_value, attr):
                pass

    assert str(exc_info.value) == ".watch decorator requires at least one argument."


def test_watch_parameter_count1():

    with pytest.raises(ValueError) as exc_info:

        @default.register
        class ComponentWatch1(ComponentWatchBase):
            @public.watch("foo")
            def watchmethod(self):
                pass

    assert (
        str(exc_info.value)
        == "The .watch method `watchmethod` must have 'value', 'old_value' and 'attr' as arguments."
    )


def test_watch_parameter_count2():

    with pytest.raises(ValueError) as exc_info:

        @default.register
        class ComponentWatch(ComponentWatchBase):
            @public.watch("foo")
            def watchmethod(self, value):  # "old_value", "attr" missing
                pass

    assert (
        str(exc_info.value)
        == "The .watch method `watchmethod` must have 'value', 'old_value' and 'attr' as arguments."
    )


def test_watch_parameter_count3():

    with pytest.raises(ValueError) as exc_info:

        @default.register
        class ComponentWatch(ComponentWatchBase):
            @public.watch("foo")
            def watchmethod(self, value, old_value):  # "attr" missing
                pass

    assert (
        str(exc_info.value)
        == "The .watch method `watchmethod` must have 'value', 'old_value' and 'attr' as arguments."
    )


def test_watch_parameter_names():

    with pytest.raises(ValueError) as exc_info:

        @default.register
        class ComponentWatch(ComponentWatchBase):
            @public.watch("foo")
            def watchmethod(self, foo, bar, baz):  # wrong names
                pass

    assert (
        str(exc_info.value)
        == "The .watch method `watchmethod` must have 'value', 'old_value' and 'attr' as arguments."
    )
