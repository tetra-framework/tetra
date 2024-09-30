from bs4 import BeautifulSoup
from django.urls import reverse
from django.template.exceptions import TemplateSyntaxError

from tests.conftest import extract_component
from tests.main.helpers import render_component
import pytest


def test_basic_component(request):
    """Tests a simple component with / end"""
    content = render_component(request, "{% @ main.default.SimpleBasicComponent / %}")
    assert extract_component(content) == "foo"


def test_basic_component_with_end_tag(request):
    """Tests a simple component with  /@ end tag"""
    content = render_component(
        request, "{% @ main.default.SimpleBasicComponent %}{% /@ %}"
    )
    assert extract_component(content) == "foo"


def test_basic_component_with_end_tag_and_name(request):
    """Tests a simple component with `/@ <name>` end tag"""
    content = render_component(
        request,
        "{% @ main.default.SimpleBasicComponent %}{% /@ SimpleBasicComponent %}",
    )
    assert extract_component(content) == "foo"


def test_basic_component_with_missing_end_tag(request):
    """Tests a simple component without end tag - must produce TemplateSyntaxError"""
    with pytest.raises(TemplateSyntaxError):
        render_component(
            request,
            "{% @ main.default.SimpleBasicComponent %}",
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
