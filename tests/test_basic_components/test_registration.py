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
    """create a lib and register a component manually and make sure it exists in the library"""
    lib1 = Library("lib1", current_app)
    lib1.register(Component1)
    assert lib1.components["component1"] is Component1


def test_register_decorator(current_app):
    """get a registered library with  a component registered there using the decorator
    syntax and make sure it exists in the library"""
    lib2 = Library("lib2", current_app)
    assert lib2.components["component2"] is Component2


def test_template_name_attr():
    """`template_name` should not be allowed as attribute"""
    with pytest.raises(NotImplementedError):

        class SomeComponent(BasicComponent):
            template_name = "no_available_template.html"
