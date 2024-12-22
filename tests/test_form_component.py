import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.cache import SessionStore
from django.test import RequestFactory

from tests.conftest import extract_component
from tests.main.helpers import render_component_tag


@pytest.mark.django_db
def test_form_component(request_with_session):
    """Tests a simple component with a dict attribute"""

    content = render_component_tag(
        request_with_session,
        "{% @ " "main.forms.SimpleFormComponent / %}",
    )
    assert (
        extract_component(content, innerHTML=True)
        == """<input id="id_first_name" maxlength="100" name="first_name" required="" type="text" value="John" x-model="first_name"/>"""
    )
