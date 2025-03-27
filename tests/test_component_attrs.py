from utils import extract_component_tag
from tests.main.helpers import render_component_tag


def test_attrs(request):
    """Tests a simple component with / end"""
    content = render_component_tag(
        request, "{% @ main.default.SimpleComponentWithAttrs / %}"
    )
    soup = extract_component_tag(content)
    assert soup.text == "content"
    assert "class1" in soup.attrs["class"]


def test_attrs_merge(request):
    """Tests a simple component with / end"""
    content = render_component_tag(
        request, "{% @ main.default.SimpleComponentWithAttrs attrs: class='class2' / %}"
    )
    soup = extract_component_tag(content)
    assert set(soup.attrs["class"]) == {"class1", "class2"}
