import re

from bs4 import BeautifulSoup
from django.urls import reverse
from django.template.exceptions import TemplateSyntaxError

from main.components.default import SimpleBasicComponent
from tests.utils import extract_component_tag
from tests.main.helpers import render_component_tag
import pytest

from tetra import Component, Library
from tetra.exceptions import ComponentNotFound


def test_basic_component_explicit_default(tetra_request):
    """Tests a simple component with / end"""
    content = render_component_tag(
        tetra_request, "{% default.SimpleBasicComponent / %}"
    )
    assert extract_component_tag(content).text == "foo"


def test_basic_component_as_default(tetra_request):
    """Tests a simple component that implicitly is found in the default library"""
    content = render_component_tag(tetra_request, "{% SimpleBasicComponent / %}")
    assert extract_component_tag(content).text == "foo"


def test_basic_component_with_explicit_library_name(tetra_request):
    with pytest.raises(TemplateSyntaxError) as exc_info:
        """Tests a simple component that is can't be found in the current_app.default
        library."""
        content = render_component_tag(tetra_request, "{% default.FooBar / %}")


def test_basic_component_with_end_tag(tetra_request):
    """Tests a simple component with  /@ end tag"""
    content = render_component_tag(
        tetra_request, "{% SimpleBasicComponent %}{% /SimpleBasicComponent %}"
    )
    assert extract_component_tag(content).text == "foo"


def test_basic_component_with_end_tag_and_name(tetra_request):
    """Tests a simple component with `/@ <name>` end tag"""
    content = render_component_tag(
        tetra_request,
        "{% SimpleBasicComponent %}{% /SimpleBasicComponent %}",
    )
    assert extract_component_tag(content).text == "foo"


def test_basic_component_with_missing_end_tag(tetra_request):
    """Tests a simple component without end tag - must produce TemplateSyntaxError"""
    with pytest.raises(TemplateSyntaxError):
        render_component_tag(
            tetra_request,
            "{% SimpleBasicComponent %}",
        )


def test_component_css_link_generation(client):
    """Tests a component with CSS file"""
    response = client.get(reverse("simple_basic_component_with_css"))
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    # it should be the only link in the header... TODO: make that more fool-proof
    link = soup.head.link["href"]
    assert link is not None
    assert re.match(r"/static/main/tetra/default/main_default-[A-Z0-9]+.css", link)
    # TODO we can't test the actual file content of the CSS file here, as static files
    #  seem not to  be available in testing  - have to figure out how
    # response = client.get(static(link))
    # assert response.status_code == 200
    # assert b".text-red { color: red; }" in response.content


# ---------- Dynamic components ------------


def test_basic_dynamic_component(tetra_request):
    """Tests a simple dynamic component"""
    content = render_component_tag(
        tetra_request,
        "{% component =dynamic_component /%}",
        {"dynamic_component": SimpleBasicComponent},
    )
    assert extract_component_tag(content).text == "foo"


def test_basic_dynamic_non_existing_component(tetra_request):
    """Tests a simple non-existing component - must produce ComponentNotFound"""
    with pytest.raises(ComponentNotFound):
        render_component_tag(
            tetra_request,
            "{% component =foo.bar.NotExistingComponent /%}",
        )


# ---------- livevar  ------------

default = Library("default", "main")


@default.register
class LiveVarComponent(Component):
    name = "foo"
    template = """
    <div id='component'>{% livevar name %}</div>
    """


def test_livevar_tag(request_with_session):
    """Tests a simple dynamic component"""
    content = render_component_tag(
        request_with_session,
        "{% LiveVarComponent /%}",
    )
    assert str(extract_component_tag(content).contents[0]) == (
        '<span x-show="name" x-text="name"></span>'
    )


@default.register
class LiveVarComponentWithCustomTag(Component):
    name = "foo"
    template = """
    <div id='component'>{% livevar name tag='bluff' %}</div>
    """


def test_livevar_tag_with_custom_tag(request_with_session):
    """Tests a simple dynamic component"""
    content = render_component_tag(
        request_with_session,
        "{% LiveVarComponentWithCustomTag /%}",
    )
    assert str(extract_component_tag(content).contents[0]) == (
        '<bluff x-show="name" x-text="name"></bluff>'
    )
