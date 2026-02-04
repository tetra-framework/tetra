import pytest
from tetra import BasicComponent, Component
from tetra.components.base import BaseRenderer
from django.utils.safestring import mark_safe


class CustomRenderer(BaseRenderer):
    def render(self, **kwargs):
        return mark_safe("Custom Rendered Content")


def test_custom_renderer(tetra_request):
    """Test that a component can use a custom renderer subclass."""

    class MyComponent(BasicComponent):
        template = "<div>Original</div>"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.renderer = CustomRenderer(self)

    comp = MyComponent(tetra_request)
    assert comp.render() == "Custom Rendered Content"


def test_renderer_extension(tetra_request):
    """Test extending ComponentRenderer to wrap component HTML with custom markup."""
    from tetra.components.base import ComponentRenderer

    class MyComponentRenderer(ComponentRenderer):
        def render(self, **kwargs):
            html = super().render(**kwargs)
            return mark_safe(f"<div class='wrapper'>{html}</div>")

    class MyComponent(Component):
        template = "<span>Inner</span>"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.renderer = MyComponentRenderer(self)

        def _encoded_state(self):
            return "mock-state"

    MyComponent._library = type(
        "obj",
        (object,),
        {"app": type("obj", (object,), {"label": "myapp"})(), "name": "mylib"},
    )()
    comp = MyComponent(tetra_request, key="mykey")
    rendered = comp.render()
    assert "<div class='wrapper'>" in rendered
    assert "Inner</span>" in rendered
    assert "x-data" in rendered
    assert "tetra-component-id" in rendered
    assert "tetra-component" in rendered
