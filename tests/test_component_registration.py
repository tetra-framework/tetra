from tetra import Library, BasicComponent


# TestComponent will be registered manually
class TestComponent1(BasicComponent):
    template = """<div></div>"""


lib2 = Library("lib2", app="main")


@lib2.register
class TestComponent2(BasicComponent):
    template = """<div></div>"""


def test_register_component_manually(current_app):
    """create a lib and register a component manually and make sure it exists in the library"""
    lib1 = Library("lib1", current_app)
    lib1.register(TestComponent1)
    assert lib1.components["test_component1"] is TestComponent1


def test_register_decorator(current_app):
    """get a registered library with  a component registered there using the decorator
    syntax and make sure it exists in the library"""
    lib2 = Library("lib2", current_app)
    assert lib2.components["test_component2"] is TestComponent2
