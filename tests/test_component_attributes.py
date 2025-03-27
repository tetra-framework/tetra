from sourcetypes import django_html

from tetra import Library, BasicComponent
from tests.conftest import extract_component_tag
from tests.main.helpers import render_component_tag


def test_simple_component_attribute_str(request_with_session):
    """Tests a simple component with a str attribute"""

    content = render_component_tag(
        request_with_session,
        "{% @ main.default.SimpleComponentWithAttributeStr / %}",
    )
    assert extract_component(content, innerHTML=True) == "str: foo"
    component = libraries["main"]["default"].components.get(
        "simple_component_with_attribute_str"
    )
    assert component.my_str == "foo"


def test_simple_component_attribute_int(request_with_session):
    """Tests a simple component with an int attribute"""

    content = render_component_tag(
        request_with_session, "{% @ main.default.SimpleComponentWithAttributeInt / %}"
    )
    assert extract_component(content, innerHTML=True) == "int: 23"
    # get handler for the component class
    component = Library.registry["main"]["default"].components.get(
        "simple_component_with_attribute_int"
    )
    assert component.my_int == 23


def test_simple_component_attribute_float(request_with_session):
    """Tests a simple component with a float attribute"""

    content = render_component_tag(
        request_with_session, "{% @ main.default.SimpleComponentWithAttributeFloat / %}"
    )
    assert extract_component(content, innerHTML=True) == "float: 2.32"


def test_simple_component_attribute_list(request_with_session):
    """Tests a simple component with a list attribute"""

    content = render_component_tag(
        request_with_session, "{% @ main.default.SimpleComponentWithAttributeList / %}"
    )
    assert extract_component(content, innerHTML=True) == "list: [1, 2, 3]"
    component = libraries["main"]["default"].components.get(
        "simple_component_with_attribute_list"
    )
    assert component.my_list == [1, 2, 3]


def test_simple_component_attribute_dict(request_with_session):
    """Tests a simple component with a dict attribute"""

    content = render_component_tag(
        request_with_session, "{% @ main.default.SimpleComponentWithAttributeDict / %}"
    )
    assert extract_component(content, innerHTML=True) == "dict: {'key': 'value'}"
    component = libraries["main"]["default"].components.get(
        "simple_component_with_attribute_dict"
    )
    assert component.my_dict == {"key": "value"}


def test_simple_component_attribute_set(request_with_session):
    """Tests a simple component with a set attribute"""

    content = render_component_tag(
        request_with_session, "{% @ main.default.SimpleComponentWithAttributeSet / %}"
    )
    assert extract_component(content, innerHTML=True) == "set: {1, 2, 3}"
    component = libraries["main"]["default"].components.get(
        "simple_component_with_attribute_set"
    )
    assert component.my_set == {1, 2, 3}


def test_simple_component_attribute_frozenset(request_with_session):
    """Tests a simple component with a frozenset attribute"""

    content = render_component_tag(
        request_with_session,
        "{% @ main.default.SimpleComponentWithAttributeFrozenSet / %}",
    )
    assert (
        extract_component(content, innerHTML=True) == "frozenset: frozenset({1, 2, 3})"
    )


def test_simple_component_attribute_bool(request_with_session):
    """Tests a simple component with a bool attribute"""

    content = render_component_tag(
        request_with_session,
        "{% @ main.default.SimpleComponentWithAttributeBool / %}",
    )
    assert extract_component(content, innerHTML=True) == "bool: False"
    component = libraries["main"]["default"].components.get(
        "simple_component_with_attribute_bool"
    )
    assert component.my_bool is False
