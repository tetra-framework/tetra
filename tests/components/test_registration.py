import pytest

from tetra.helpers import render_component_tag
from tetra import Library, BasicComponent


# TestComponent will be registered manually
class Component1(BasicComponent):
    template = """<div></div>"""


lib2 = Library("lib2", app="main")


@lib2.register
class Component2(BasicComponent):
    template = """<div></div>"""


def test_register_component_manually(current_app):
    """Verify that a component can be manually registered with a Library and retrieved."""
    lib1 = Library("lib1", current_app)
    lib1.register(Component1)
    assert lib1.components["component1"] is Component1


def test_register_decorator(current_app):
    """Verify that a component is correctly registered with a Library using the @register decorator."""
    lib2 = Library("lib2", current_app)
    assert lib2.components["component2"] is Component2


def test_template_name_attr():
    """Verify that using 'template_name' as a component attribute raises a NotImplementedError."""
    with pytest.raises(NotImplementedError):

        class SomeComponent(BasicComponent):
            template_name = "no_available_template.html"
