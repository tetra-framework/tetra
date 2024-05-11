from bs4 import BeautifulSoup
from django.urls import reverse
from django.template.exceptions import TemplateSyntaxError

from tests.conftest import extract_component
from tests.main.helpers import render_component
import pytest


def test_basic_component(request):
    """Tests a simple component with / end"""
    content = render_component(
        request, "{% @ main.default.simple_component_with_attrs / %}"
    )
    assert extract_component(content) == "content"
    assert (
        extract_component(content, innerHTML=False)
        == '<div class="class1" id="component">content</div>'
    )
