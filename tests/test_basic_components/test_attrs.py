from utils import extract_component_tag
from tetra.helpers import render_component_tag


def test_attrs(tetra_request):
    """Verify that extra attributes passed to a component are correctly rendered on the root element."""
    content = render_component_tag(tetra_request, "{% SimpleComponentWithAttrs / %}")
    soup = extract_component_tag(content)
    assert soup.text == "content"
    assert "class1" in soup.attrs["class"]


def test_attrs_merge(tetra_request):
    """Verify that attributes passed via 'attrs:' are correctly merged with existing attributes on the component."""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithAttrs attrs: class='class2' / %}",
    )
    soup = extract_component_tag(content)
    assert set(soup.attrs["class"]) == {"class1", "class2"}
