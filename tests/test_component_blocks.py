from tests.utils import extract_component_tag
from tests.main.helpers import render_component_tag


def test_component_with_default_slot(tetra_request):
    """Tests a simple component with default slot"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithDefaultBlock %}content{% /SimpleComponentWithDefaultBlock %}",
    )
    assert extract_component_tag(content).text == "content"


def test_component_with_named_slot(tetra_request):
    """Tests a simple component with empty default slot (unfilled)"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == ""


def test_component_with_named_slot_and_content(tetra_request):
    """Tests a simple component with "foo" slot"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}"
        "{% slot foo %}foo{% endslot %}"
        "{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == "foo"


def test_component_with_named_slot_and_default_content(tetra_request):
    """Tests a simple component with "foo" slot and default content in it"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlockWithContent %}"
        "{% /SimpleComponentWithNamedBlockWithContent %}",
    )
    assert extract_component_tag(content).text == "foo"


def test_component_with_notexisting_slot_and_content(tetra_request):
    """Tests a simple component with notexisting slot filled. Must be ignored."""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}"
        "{% slot notexisting %}foo{% endslot %}"
        "{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == ""


def test_component_with_named_slot_empty(tetra_request):
    """Tests a simple component named"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}"
        "{% slot foo %}{% endslot %}"
        "{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == ""


# FIXME: this test does not work correctly
# def test_component_with_named_slot_and_content_outside_slot_ignored(request):
#     """Tests a simple component with content outside of slots. Must not be rendered."""
#     content = render_component(
#         request,
#         """
# {% SimpleComponentWithNamedBlock %}
# abracadabra
# {% slot foo %}inside{% endslot %}
# {% /SimpleComponentWithNamedBlock %}
# """,
#     )
#     assert extract_component(content) == "inside"


def test_component_with_2_slots_unfilled(tetra_request):
    """Tests a simple component with `foo` and `default` slots unfilled. Default
    slot contains some default content"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWith2Blocks %}"
        "{% slot foo %}{% endslot %}"
        "{% /SimpleComponentWith2Blocks %}",
    )
    assert extract_component_tag(content).text == "default"


def test_component_with_2_slots_partly_filled(tetra_request):
    """Tests a simple component with 2 blocks partly filled"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWith2Blocks %}"
        "{% slot foo %}bar{% endslot %}"
        "{% /SimpleComponentWith2Blocks %}",
    )
    assert extract_component_tag(content).text == "defaultbar"


def test_component_with_slot_and_default_content_overridden(tetra_request):
    """Tests a simple component overridden default content"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}"
        "{% slot foo %}overridden{% endslot %}"
        "{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == "overridden"


def test_component_with_conditional_slot_empty(tetra_request):
    """Tests a simple component with conditional slot that is not rendered,
    as it is empty
    """
    content = render_component_tag(
        tetra_request, "{% SimpleComponentWithConditionalBlock / %}"
    )
    assert extract_component_tag(content).text == "always"


def test_component_with_conditional_slot_filled_empty(tetra_request):
    """Tests a simple component with default content, that is overridden with empty
    slot.
    """
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithConditionalBlock  %}"
        "{% slot foo %}{% endslot %}"
        "{% /SimpleComponentWithConditionalBlock %}",
    )
    assert extract_component_tag(content).decode_contents() == "BEFOREAFTERalways"


def test_component_with_conditional_slot_filled(tetra_request):
    """Tests a simple component with conditional slot, filled, with mixed text from
    component and slot overrides."""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithConditionalBlock  %}"
        "{% slot foo %}foo{% endslot %}"
        "{% /SimpleComponentWithConditionalBlock %}",
    )
    assert extract_component_tag(content).decode_contents() == "BEFOREfooAFTERalways"


def test_component_with_conditional_addcontent_slot_filled(tetra_request):
    """Tests a simple component with conditional slot, filled, with mixed text from
    component and slot overrides."""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithConditionalBlockAndAdditionalContent %}"
        "{% slot foo %}foo{% endslot %}"
        "{% /SimpleComponentWithConditionalBlockAndAdditionalContent %}",
    )
    assert extract_component_tag(content).decode_contents() == "BEFOREfooAFTER"


def test_component_with_conditional_addcontent_slot_filled_and_html_tags(
    tetra_request,
):
    """Tests a simple component with conditional slot, filled, with html tags"""
    content = render_component_tag(
        tetra_request,
        """
{% SimpleComponentWithConditionalBlockAndAdditionalHtmlContent %}
{% slot foo %}bar{% endslot %}
{% /SimpleComponentWithConditionalBlockAndAdditionalHtmlContent %}
""",
    )
    assert (
        extract_component_tag(content).decode_contents().replace("\n", "")
        == "<div><span>bar</span></div>"
    )
