from conftest import current_app
from tetra import Library, BasicComponent

# FIXME "main" is hardcoded here - how can we reuse the fixture as it cannot be called
#  directly
default = Library("default", app="main")


class TestComponent(BasicComponent):
    template = """<div></div>"""


@default.register
class TestComponent2(BasicComponent):
    template = """<div></div>"""


def test_register_decorator(current_app):
    """register a component using the decorator and make sure it exists in the library"""
    lib = Library("default", app=current_app)
    assert lib.components["test_component2"] is TestComponent2


def test_register_component_manually(current_app):
    """create a lib and register a component manually and make sure it exists in the library"""
    lib = Library("default", app=current_app)
    lib.register(TestComponent)
    assert lib.components["test_component"] is TestComponent
