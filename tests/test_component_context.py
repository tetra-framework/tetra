from tests.utils import extract_component_tag
from tests.main.helpers import render_component_tag


def test_use_extra_context_not_scoped(tetra_request):
    """Component may not display outer context vars, if not explicitly included."""
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithDefaultBlock %}"
        "{{foo}}"
        "{% /SimpleComponentWithDefaultBlock %}",
        context={"foo": "bar"},  # global, outer context
    )
    assert extract_component_tag(content).text == ""


def test_use_extra_context(tetra_request):
    """Component must display outer context vars, if explicitly included in
    _extra_context."""
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithFooContext %}"
        "{{foo}}"
        "{% /SimpleComponentWithFooContext %}",
        context={"foo": "bar"},  # global, outer context
    )
    assert extract_component_tag(content).text == "bar"


def test_use_extra_context_empty(tetra_request):
    """Component must not display outer context vars, if explicitly included in
    _extra_context, but var==empty."""
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithFooContext %}"
        "{{foo}}"
        "{% /SimpleComponentWithFooContext %}",  # FIXME:KeyError(key)
        # context={"foo": "bar"},  # global, outer context
    )
    assert extract_component_tag(content).text == ""


def test_use_extra_context_all_empty(tetra_request):
    """Component must not display outer context vars, if _extra_context == __all__,
    but var==empty."""
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithExtraContextAll %}"
        "{{foo}}"
        "{% /SimpleComponentWithExtraContextAll %}",
        # context={"foo": "bar"},  # global, outer context
    )
    assert extract_component_tag(content).text == ""


def test_use_extra_context_all(tetra_request):
    """Component must display outer context vars, if __all__ in _extra_context."""
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithExtraContextAll %}"
        "{{foo}}"
        "{% /SimpleComponentWithExtraContextAll %}",
        context={"foo": "bar"},  # global, outer context
    )
    assert extract_component_tag(content).text == "bar"


# -------- using template attrs --------


def test_use_context_attr(tetra_request):
    """context must be available when ctx var explicitly given on template calling"""
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithDefaultBlock "
        "context: foo='bar' %}"
        "{{foo}}"
        "{% /SimpleComponentWithDefaultBlock %}",
    )
    assert extract_component_tag(content).text == "bar"


def test_use_context_attr_all(tetra_request):
    """context must be available when ctx == all on template calling"""
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithDefaultBlock "
        "context: __all__ %}"
        "{{foo}}"
        "{% /SimpleComponentWithDefaultBlock %}",
        context={"foo": "bar"},  # global, outer context
    )
    assert extract_component_tag(content).text == "bar"


def test_extra_context(tetra_request):
    """_extra_context must be available automatically."""
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithExtraContextAll %}"
        "{{foo}}"
        "{% /SimpleComponentWithExtraContextAll %}",
        context={"foo": "bar"},  # global, outer context, included in __all__
    )
    assert extract_component_tag(content).text == "bar"


def test_context_attr_overrides_extra_context(tetra_request):
    """context given at the template tag must override the outer context."""
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithExtraContextAll "
        "context: foo='nobaz' %}"
        "{{foo}}"
        "{% /SimpleComponentWithExtraContextAll %}",
    )
    assert extract_component_tag(content).text == "nobaz"
