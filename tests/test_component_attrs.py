
from tests.conftest import extract_component
from tests.main.helpers import render_component_tag


def test_basic_component(request):
    """Tests a simple component with / end"""
    content = render_component_tag(
        request, "{% @ main.default.SimpleComponentWithAttrs / %}"
    )
    assert extract_component(content) == "content"
    assert (
        extract_component(content, innerHTML=False)
        == '<div class="class1" id="component">content</div>'
    )
