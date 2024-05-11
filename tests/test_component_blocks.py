from tests.conftest import extract_component
from tests.main.helpers import render_component


def test_component_with_default_block(request):
    """Tests a simple component with default block"""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_default_block %}content{% /@ %}",
    )
    assert extract_component(content) == "content"


def test_component_with_named_block(request):
    """Tests a simple component with empty default block (unfilled)"""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_named_block %}{% /@ %}",
    )
    assert extract_component(content) == ""


def test_component_with_named_block_and_content(request):
    """Tests a simple component with "foo" block"""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_named_block %}"
        "{% block foo %}foo{% endblock %}"
        "{% /@ %}",
    )
    assert extract_component(content) == "foo"


def test_component_with_named_block_and_default_content(request):
    """Tests a simple component with "foo" block and default content in it"""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_named_block_with_content %}"
        "{% /@ %}",
    )
    assert extract_component(content) == "foo"


def test_component_with_notexisting_block_and_content(request):
    """Tests a simple component with notexisting block filled. Must be ignored."""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_named_block %}"
        "{% block notexisting %}foo{% endblock %}"
        "{% /@ %}",
    )
    assert extract_component(content) == ""


def test_component_with_named_block_empty(request):
    """Tests a simple component named"""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_named_block %}"
        "{% block foo %}{% endblock %}"
        "{% /@ %}",
    )
    assert extract_component(content) == ""


# FIXME: this test does not work correctly
# def test_component_with_named_block_and_content_outside_block_ignored(request):
#     """Tests a simple component with content outside of blocks. Must not be rendered."""
#     content = render_component(
#         request,
#         """
# {% @ main.default.simple_component_with_named_block %}
# abracadabra
# {% block foo %}inside{% endblock %}
# {% /@ %}
# """,
#     )
#     assert extract_component(content) == "inside"


def test_component_with_2_blocks_unfilled(request):
    """Tests a simple component with `foo` and `default` blocks unfilled. Default
    block contains some default content"""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with2_blocks %}"
        "{% block foo %}{% endblock %}"
        "{% /@ %}",
    )
    assert extract_component(content) == "default"


def test_component_with_2_blocks_partly_filled(request):
    """Tests a simple component with 2 blocks partly filled"""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with2_blocks %}"
        "{% block foo %}bar{% endblock %}"
        "{% /@ %}",
    )
    assert extract_component(content) == "defaultbar"


def test_component_with_block_and_default_content_overridden(request):
    """Tests a simple component overridden default content"""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_named_block %}"
        "{% block foo %}overridden{% endblock %}"
        "{% /@ %}",
    )
    assert extract_component(content) == "overridden"


def test_component_with_conditional_block_empty(request):
    """Tests a simple component with conditional block that is not rendered,
    as it is empty
    """
    content = render_component(
        request, "{% @ main.default.simple_component_with_conditional_block / %}"
    )
    assert extract_component(content) == "always"


def test_component_with_conditional_block_filled_empty(request):
    """Tests a simple component with default content, that is overridden with empty
    block.
    """
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_conditional_block  %}"
        "{% block foo %}{% endblock %}"
        "{% /@ %}",
    )
    assert extract_component(content) == "BEFOREAFTERalways"


def test_component_with_conditional_block_filled(request):
    """Tests a simple component with conditional block, filled, with mixed text from
    component and block overrides."""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_conditional_block  %}"
        "{% block foo %}foo{% endblock %}"
        "{% /@ %}",
    )
    assert extract_component(content) == "BEFOREfooAFTERalways"


def test_component_with_conditional_addcontent_block_filled(request):
    """Tests a simple component with conditional block, filled, with mixed text from
    component and block overrides."""
    content = render_component(
        request,
        "{% @ main.default.simple_component_with_conditional_block_and_additional_content %}"
        "{% block foo %}foo{% endblock %}"
        "{% /@ %}",
    )
    assert extract_component(content) == "BEFOREfooAFTER"


def test_component_with_conditional_addcontent_block_filled_and_html_tags(request):
    """Tests a simple component with conditional block, filled, with html tags"""
    content = render_component(
        request,
        """
{% @ main.default.simple_component_with_conditional_block_and_additional_html_content %}
{% block foo %}foo{% endblock %}
{% /@ %}
""",
    )
    assert extract_component(content) == "<div><span>foo</span></div>"
