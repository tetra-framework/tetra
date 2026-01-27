import pytest
from pydantic import ValidationError
from django import forms
from tetra import Library, public
from tetra.components.base import FormComponent
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser

my_lib = Library("test_form_pydantic", "main")


class RequiredForm(forms.Form):
    name = forms.CharField(required=True)
    age = forms.IntegerField(required=False)


@my_lib.register
class RequiredFormComponent(FormComponent):
    form_class = RequiredForm
    template = "<div></div>"


def get_request_with_session():
    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


@pytest.mark.django_db
def test_form_pydantic_validation():
    request = get_request_with_session()
    comp = RequiredFormComponent(request)

    # All form fields should allow None in the component state, regardless of
    # required=True/False, because they might be empty before user interaction.
    # Validation happens at the form layer, not the state layer.
    comp.age = None
    comp.name = "John"
    comp._encoded_state()

    comp.name = None
    comp._encoded_state()
