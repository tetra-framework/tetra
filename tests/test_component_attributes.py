from sourcetypes import django_html

from tetra import Library, BasicComponent
from tests.main.helpers import render_component_tag
from utils import extract_component_tag

attrs = Library("attrs", "main")


@attrs.register
class SimpleComponentWithAttributeStr(BasicComponent):
    my_str: str = "foo"
    template: django_html = "<div id='component'>str: {{ my_str }}</div>"


def test_simple_component_attribute_str(request_with_session):
    """Tests a simple component with a str attribute"""
    content = render_component_tag(
        request_with_session,
        "{% attrs.SimpleComponentWithAttributeStr / %}",
    )
    soup = extract_component_tag(content)
    assert soup.text == "str: foo"
    component = Library.registry["main"]["attrs"].components.get(
        "simple_component_with_attribute_str"
    )
    assert component.my_str == "foo"


def test_simple_component_attribute_int(request_with_session):
    """Tests a simple component with an int attribute"""

    content = render_component_tag(
        request_with_session, "{% SimpleComponentWithAttributeInt / %}"
    )
    soup = extract_component_tag(content)

    assert soup.text == "int: 23"
    # get handler for the component class
    component = Library.registry["main"]["default"].components.get(
        "simple_component_with_attribute_int"
    )
    assert component.my_int == 23


def test_simple_component_attribute_float(request_with_session):
    """Tests a simple component with a float attribute"""

    content = render_component_tag(
        request_with_session, "{% SimpleComponentWithAttributeFloat / %}"
    )
    assert extract_component_tag(content).text == "float: 2.32"


def test_simple_component_attribute_list(request_with_session):
    """Tests a simple component with a list attribute"""

    content = render_component_tag(
        request_with_session, "{% SimpleComponentWithAttributeList / %}"
    )
    soup = extract_component_tag(content)
    assert soup.text == "list: [1, 2, 3]"
    component = Library.registry["main"]["default"].components.get(
        "simple_component_with_attribute_list"
    )
    assert component.my_list == [1, 2, 3]


def test_simple_component_attribute_dict(request_with_session):
    """Tests a simple component with a dict attribute"""

    content = render_component_tag(
        request_with_session, "{% SimpleComponentWithAttributeDict / %}"
    )
    soup = extract_component_tag(content)
    assert soup.text == "dict: {'key': 'value'}"
    component = Library.registry["main"]["default"].components.get(
        "simple_component_with_attribute_dict"
    )
    assert component.my_dict == {"key": "value"}


def test_simple_component_attribute_set(request_with_session):
    """Tests a simple component with a set attribute"""

    content = render_component_tag(
        request_with_session, "{% SimpleComponentWithAttributeSet / %}"
    )
    soup = extract_component_tag(content)
    assert soup.text == "set: {1, 2, 3}"
    component = Library.registry["main"]["default"].components.get(
        "simple_component_with_attribute_set"
    )
    assert component.my_set == {1, 2, 3}


def test_simple_component_attribute_frozenset(request_with_session):
    """Tests a simple component with a frozenset attribute"""

    content = render_component_tag(
        request_with_session,
        "{% SimpleComponentWithAttributeFrozenSet / %}",
    )
    soup = extract_component_tag(content)
    assert soup.text == "frozenset: frozenset({1, 2, 3})"


def test_simple_component_attribute_bool(request_with_session):
    """Tests a simple component with a bool attribute"""

    content = render_component_tag(
        request_with_session,
        "{% SimpleComponentWithAttributeBool / %}",
    )
    soup = extract_component_tag(content)
    assert soup.text == "bool: False"
    component = Library.registry["main"]["default"].components.get(
        "simple_component_with_attribute_bool"
    )
    assert component.my_bool is False
