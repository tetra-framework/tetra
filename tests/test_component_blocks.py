from tests.utils import extract_component_tag
from tests.main.helpers import render_component_tag


def test_component_with_default_block(tetra_request):
    """Tests a simple component with default block"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithDefaultBlock %}content{% /SimpleComponentWithDefaultBlock %}",
    )
    assert extract_component_tag(content).text == "content"


def test_component_with_named_block(tetra_request):
    """Tests a simple component with empty default block (unfilled)"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == ""


def test_component_with_named_block_and_content(tetra_request):
    """Tests a simple component with "foo" block"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}"
        "{% block foo %}foo{% endblock %}"
        "{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == "foo"


def test_component_with_named_block_and_default_content(tetra_request):
    """Tests a simple component with "foo" block and default content in it"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlockWithContent %}"
        "{% /SimpleComponentWithNamedBlockWithContent %}",
    )
    assert extract_component_tag(content).text == "foo"


def test_component_with_notexisting_block_and_content(tetra_request):
    """Tests a simple component with notexisting block filled. Must be ignored."""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}"
        "{% block notexisting %}foo{% endblock %}"
        "{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == ""


def test_component_with_named_block_empty(tetra_request):
    """Tests a simple component named"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}"
        "{% block foo %}{% endblock %}"
        "{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == ""


# FIXME: this test does not work correctly
# def test_component_with_named_block_and_content_outside_block_ignored(request):
#     """Tests a simple component with content outside of blocks. Must not be rendered."""
#     content = render_component(
#         request,
#         """
# {% SimpleComponentWithNamedBlock %}
# abracadabra
# {% block foo %}inside{% endblock %}
# {% /SimpleComponentWithNamedBlock %}
# """,
#     )
#     assert extract_component(content) == "inside"


def test_component_with_2_blocks_unfilled(tetra_request):
    """Tests a simple component with `foo` and `default` blocks unfilled. Default
    block contains some default content"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWith2Blocks %}"
        "{% block foo %}{% endblock %}"
        "{% /SimpleComponentWith2Blocks %}",
    )
    assert extract_component_tag(content).text == "default"


def test_component_with_2_blocks_partly_filled(tetra_request):
    """Tests a simple component with 2 blocks partly filled"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWith2Blocks %}"
        "{% block foo %}bar{% endblock %}"
        "{% /SimpleComponentWith2Blocks %}",
    )
    assert extract_component_tag(content).text == "defaultbar"


def test_component_with_block_and_default_content_overridden(tetra_request):
    """Tests a simple component overridden default content"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithNamedBlock %}"
        "{% block foo %}overridden{% endblock %}"
        "{% /SimpleComponentWithNamedBlock %}",
    )
    assert extract_component_tag(content).text == "overridden"


def test_component_with_conditional_block_empty(tetra_request):
    """Tests a simple component with conditional block that is not rendered,
    as it is empty
    """
    content = render_component_tag(
        tetra_request, "{% SimpleComponentWithConditionalBlock / %}"
    )
    assert extract_component_tag(content).text == "always"


def test_component_with_conditional_block_filled_empty(tetra_request):
    """Tests a simple component with default content, that is overridden with empty
    block.
    """
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithConditionalBlock  %}"
        "{% block foo %}{% endblock %}"
        "{% /SimpleComponentWithConditionalBlock %}",
    )
    assert extract_component_tag(content).decode_contents() == "BEFOREAFTERalways"


def test_component_with_conditional_block_filled(tetra_request):
    """Tests a simple component with conditional block, filled, with mixed text from
    component and block overrides."""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithConditionalBlock  %}"
        "{% block foo %}foo{% endblock %}"
        "{% /SimpleComponentWithConditionalBlock %}",
    )
    assert extract_component_tag(content).decode_contents() == "BEFOREfooAFTERalways"


def test_component_with_conditional_addcontent_block_filled(tetra_request):
    """Tests a simple component with conditional block, filled, with mixed text from
    component and block overrides."""
    content = render_component_tag(
        tetra_request,
        "{% SimpleComponentWithConditionalBlockAndAdditionalContent %}"
        "{% block foo %}foo{% endblock %}"
        "{% /SimpleComponentWithConditionalBlockAndAdditionalContent %}",
    )
    assert extract_component_tag(content).decode_contents() == "BEFOREfooAFTER"


def test_component_with_conditional_addcontent_block_filled_and_html_tags(
    tetra_request,
):
    """Tests a simple component with conditional block, filled, with html tags"""
    content = render_component_tag(
        tetra_request,
        """
{% SimpleComponentWithConditionalBlockAndAdditionalHtmlContent %}
{% block foo %}bar{% endblock %}
{% /SimpleComponentWithConditionalBlockAndAdditionalHtmlContent %}
""",
    )
    assert (
        extract_component_tag(content).decode_contents().replace("\n", "")
        == "<div><span>bar</span></div>"
    )
