import pytest

from tetra import BasicComponent
from tetra.exceptions import ComponentError


def test_component_without_root_tag():
    with pytest.raises(ComponentError) as exc_info:

        class ComponentWithoutRootTag(BasicComponent):
            # language=html
            template = """
                This is not allowed
            """

    assert (
        "Component template 'ComponentWithoutRootTag.template' must contain exactly one top-level tag."
        in str(exc_info.value)
    )


def test_component_with_2_root_tags():
    with pytest.raises(ComponentError) as exc_info:

        class ComponentWith2RootTags(BasicComponent):
            # language=html
            template = """
                <div>Foo</div>
                <div>Bar</div>
            """

    assert (
        "Component template 'ComponentWith2RootTags.template' must contain exactly one top-level tag."
        in str(exc_info.value)
    )


def test_component_with_3_root_tags():
    with pytest.raises(ComponentError) as exc_info:

        class ComponentWith3RootTags(BasicComponent):
            # language=html
            template = """
                <div>Foo</div>
                <div>Bar</div>
                <div>Baz</div>
            """

    assert (
        "Component template 'ComponentWith3RootTags.template' must contain exactly one top-level tag."
        in str(exc_info.value)
    )


def test_component_with_empty_template():
    with pytest.raises(ComponentError) as exc_info:

        class ComponentWithEmptyTemplate(BasicComponent):
            template = ""

    assert ("Component 'ComponentWithEmptyTemplate' has an empty template.") in str(
        exc_info.value
    )


def test_component_with_no_template():
    with pytest.raises(ComponentError) as exc_info:

        class ComponentWithNoTemplate(BasicComponent):
            pass

    assert (
        "'test_templates.ComponentWithNoTemplate' is not a valid component."
    ) in str(exc_info.value)


def test_component_with_template_syntax_error():

    with pytest.raises(ComponentError) as exc_info:

        class ComponentWithTemplateSyntaxError(BasicComponent):
            # language=html
            template = """
                <div>{% invalid_tag %}</div>
            """

    assert (
        "Template compilation failed for component 'ComponentWithTemplateSyntaxError'"
    ) in str(exc_info.value)
