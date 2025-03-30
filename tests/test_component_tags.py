import re

from bs4 import BeautifulSoup
from django.urls import reverse
from django.template.exceptions import TemplateSyntaxError

from main.components.default import SimpleBasicComponent
from tests.utils import extract_component_tag
from tests.main.helpers import render_component_tag
import pytest

from tetra.exceptions import ComponentNotFound


def test_basic_component(request):
    """Tests a simple component with / end"""
    content = render_component_tag(
        request, "{% @ main.default.SimpleBasicComponent / %}"
    )
    assert extract_component_tag(content).text == "foo"


def test_basic_component_as_default(request):
    """Tests a simple component that implicitly is found in the default library"""
    content = render_component_tag(request, "{% @ main.SimpleBasicComponent / %}")
    assert extract_component_tag(content).text == "foo"


def test_basic_component_with_library(request):
    with pytest.raises(ComponentNotFound) as exc_info:
        """Tests a simple component that is can't be found in the current_app.default
        library."""
        content = render_component_tag(
            request, "{% @ default.SimpleBasicComponent / %}"
        )
    assert (
        "but there is no component 'SimpleBasicComponent' in the 'default' library of "
        "the 'default' app"
    ) in str(exc_info.value)


def test_basic_component_with_app_and_library(request):
    with pytest.raises(ComponentNotFound) as exc_info:
        content = render_component_tag(request, "{% @ SimpleBasicComponent / %}")
    assert (
        "Unable to ascertain current app. Component name 'SimpleBasicComponent' must be in "
    ) in str(exc_info.value)


def test_basic_component_with_end_tag(request):
    """Tests a simple component with  /@ end tag"""
    content = render_component_tag(
        request, "{% @ main.default.SimpleBasicComponent %}{% /@ %}"
    )
    assert extract_component_tag(content).text == "foo"


def test_basic_component_with_end_tag_and_name(request):
    """Tests a simple component with `/@ <name>` end tag"""
    content = render_component_tag(
        request,
        "{% @ main.default.SimpleBasicComponent %}{% /@ SimpleBasicComponent %}",
    )
    assert extract_component_tag(content).text == "foo"


def test_basic_component_with_missing_end_tag(request):
    """Tests a simple component without end tag - must produce TemplateSyntaxError"""
    with pytest.raises(TemplateSyntaxError):
        render_component_tag(
            request,
            "{% @ main.default.SimpleBasicComponent %}",
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


def test_basic_dynamic_component(request):
    """Tests a simple dynamic component"""
    content = render_component_tag(
        request,
        "{% @ =dynamic_component /%}",
        {"dynamic_component": SimpleBasicComponent},
    )
    assert extract_component_tag(content).text == "foo"


def test_basic_dynamic_non_existing_component(request):
    """Tests a simple non-existing component - must produce ComponentNotFound"""
    with pytest.raises(ComponentNotFound):
        render_component_tag(
            request,
            "{% @ =foo.bar.NotExistingComponent /%}",
        )
