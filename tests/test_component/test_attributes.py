from tetra import Component, Library

lib = Library("lib", "main")


@lib.register
class PersonComponent(Component):
    name: str = "John"
    age: int = 23

    template = """<div></div>"""


def test_component_key_generation(tetra_request):
    """Test that the component key is generated correctly."""

    c = PersonComponent(tetra_request)
    assert c.key == "main__lib__person_component"  # noqa
