from bs4 import BeautifulSoup
from django.urls import reverse
from django.template.exceptions import TemplateSyntaxError

from tests.conftest import extract_component
from tests.main.helpers import render_component_tag
import pytest


def test_basic_component(request):
    """Tests a simple component with / end"""
    content = render_component_tag(request, "{% @ main.default.simple_basic_component / %}")
    assert extract_component(content) == "foo"

def test_basic_component_as_default(request):
    """Tests a simple component that implicitly is found in the default library"""
    # FIXME: this does not work, as tetra does not fund the current app while in testing
    content = render_component_tag(request, "{% @ main.simple_basic_component / %}")
    assert extract_component(content) == "foo"

def test_basic_component_with_end_tag(request):
    """Tests a simple component with  /@ end tag"""
    content = render_component_tag(
        request, "{% @ main.default.simple_basic_component %}{% /@ %}"
    )
    assert extract_component(content) == "foo"


def test_basic_component_with_end_tag_and_name(request):
    """Tests a simple component with `/@ <name>` end tag"""
    content = render_component_tag(
        request,
        "{% @ main.default.simple_basic_component %}{% /@ simple_basic_component%}",
    )
    assert extract_component(content) == "foo"


def test_basic_component_with_missing_end_tag(request):
    """Tests a simple component without end tag - must produce TemplateSyntaxError"""
    with pytest.raises(TemplateSyntaxError):
        content = render_component_tag(
            request,
            "{% @ main.default.simple_basic_component %}",
        )


def test_css_component(client):
    """Tests a component with CSS file"""
    response = client.get(reverse("simple_basic_component_with_css"))
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    # it should be the only link in the header... TODO: make that more fool-proof
    link = soup.head.link["href"]
    assert "main_default" in link
    assert link is not None
    response = client.get(link)
    # FIXME: does not work yet. staticfiles problem? Should run in DEBUG mode without
    #  problem...
    # assert response.status_code == 200
    # assert b".text-red { color: red; }" in response.content
