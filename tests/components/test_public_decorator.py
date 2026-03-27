from types import MethodType

import pytest

from tetra import public, Library, Component
from utils.base_utils import extract_component_tag
from apps.main.components.default import ComponentWithPublic
from tetra.helpers import render_component_tag


def test_public_decorator_is_replaced_with_actual_method_or_attribute(tetra_request):
    # assert extract_component(content) == "mMessage"
    c = ComponentWithPublic(tetra_request)
    # make sure that @public decorated methods and attributes are replaced with their
    # actual method/attribute - they must not be "PublicMeta"
    assert type(c.msg) is str
    assert isinstance(c.do_something, MethodType)


default = Library("default", "main")


def test_listen_with_wrong_arguments():
    with pytest.raises(ValueError):

        @default.register
        class ComponentWithPublicListen(Component):
            @public.listen("keyup.enter")
            def do_something(self) -> str:  # should have event_detail as param
                pass

            template = """<div id='component' {% ... attrs %}></div>"""


@default.register
class ComponentWithPublicListen(Component):

    @public.listen("keyup.enter")
    def do_something(self, event_detail) -> str:
        pass

    template = """<div id='component' {% ... attrs %}></div>"""


def test_public_listen_renders_attrs(tetra_request):
    """Checks if a @public.listen decorator renders the attr correctly."""
    content = render_component_tag(tetra_request, "{% ComponentWithPublicListen / %}")
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


def test_notexistent_public_method():
    """When a non-existent public method is called, it should raise an AttributeError"""
    with pytest.raises(AttributeError):

        @default.register
        class SomeComponent(ComponentWatchBase):
            @public.skjghkjlh()  # wrong method name
            def foo_method(self):
                pass


def test_chained_public_decorators_possible():
    """Test that multiple public decorators can be applied to a method"""

    @default.register
    class Component2DeclaredDecoratorMethods(ComponentWatchBase):
        @public.watch("foo").debounce(100)
        def foo_method(self, value, old_value, attr):
            pass


def test_chained_public_decorators_working():
    """Test that chained public decorators actually invoke watch() and debounce()."""
    from unittest.mock import patch, MagicMock
    from tetra.components.base import Public

    mock_public_instance = MagicMock(spec=Public)
    mock_public_instance.debounce = MagicMock(return_value=mock_public_instance)

    with patch.object(Public, "do_watch", return_value=mock_public_instance) as mock_watch:
        result = public.watch("foo").debounce(100)

        mock_watch.assert_called_once_with("foo")
        mock_public_instance.debounce.assert_called_once_with(100)
