from bs4 import BeautifulSoup
from django.urls import reverse
from django.template.exceptions import TemplateSyntaxError

from tests.conftest import extract_component
from tests.main.helpers import render_component_tag
import pytest


def test_basic_component(request):
    """Tests a simple component with / end"""
    content = render_component_tag(
        request, "{% @ main.default.simple_component_with_attrs / %}"
    )
    assert extract_component(content) == "foo"
