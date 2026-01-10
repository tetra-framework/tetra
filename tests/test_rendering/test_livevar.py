from tetra.helpers import render_component_tag
from tetra import Library, Component
from utils import extract_component_tag

default = Library("default", "main")


@default.register
class LiveVarComponent(Component):
    name = "foo"
    template = """
    <div id='component'>{% livevar name %}</div>
    """


def test_livevar_tag(tetra_request):
    """Tests a simple dynamic component"""
    content = render_component_tag(
        tetra_request,
        "{% LiveVarComponent /%}",
    )
    assert str(extract_component_tag(content).contents[0]) == (
        '<span x-show="name" x-text="name"></span>'
    )


@default.register
class LiveVarComponentWithCustomTag(Component):
    name = "foo"
    template = """
    <div id='component'>{% livevar name tag='bluff' %}</div>
    """


def test_livevar_tag_with_custom_tag(tetra_request):
    """Tests a simple dynamic component"""
    content = render_component_tag(
        tetra_request,
        "{% LiveVarComponentWithCustomTag /%}",
    )
    assert str(extract_component_tag(content).contents[0]) == (
        '<bluff x-show="name" x-text="name"></bluff>'
    )
