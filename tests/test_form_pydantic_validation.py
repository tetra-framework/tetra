import pytest
from enum import Enum

from django.db.models import TextChoices
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


from django.db.models.fields.files import FieldFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models


class AccountType(TextChoices):
    PERSON = "person"
    BUSINESS = "business"


class EnumChoiceForm(forms.Form):
    account_type = forms.ChoiceField(
        choices=[(tag.value, tag.name) for tag in AccountType],
        initial=AccountType.PERSON,
    )


@my_lib.register
class EnumChoiceFormComponent(FormComponent):
    form_class = EnumChoiceForm
    template = "<div></div>"


@pytest.mark.django_db
def test_form_enum_choice_pydantic_validation():
    request = get_request_with_session()
    comp = EnumChoiceFormComponent(request)

    # Initial value is AccountType.PERSON
    assert comp.account_type == AccountType.PERSON

    # This should NOT raise ValidationError
    comp._encoded_state()

    # Setting it to the value should also work (Pydantic coercion)
    comp.account_type = "business"
    comp._encoded_state()

    # Setting it to another Enum member
    comp.account_type = AccountType.BUSINESS
    comp._encoded_state()


class FileForm(forms.Form):
    identity_proof = forms.FileField(required=False)


@my_lib.register
class FileFormComponent(FormComponent):
    form_class = FileForm
    template = "<div></div>"


class MockModel(models.Model):
    file = models.FileField(upload_to="test/")

    class Meta:
        app_label = "test_form_pydantic"


@pytest.mark.django_db
def test_form_file_field_pydantic_validation():
    request = get_request_with_session()
    comp = FileFormComponent(request)

    # Initial value is None
    assert comp.identity_proof is None
    comp._encoded_state()

    # SimpleUploadedFile
    comp.identity_proof = SimpleUploadedFile("test.txt", b"hello")
    comp._encoded_state()

    # FieldFile
    instance = MockModel()
    ff = FieldFile(instance, MockModel._meta.get_field("file"), "test.txt")
    comp.identity_proof = ff
    comp._encoded_state()
