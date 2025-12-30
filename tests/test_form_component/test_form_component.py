import pytest
from datetime import date
from unittest.mock import patch

from django import forms
from django.forms import Form
from django.urls import reverse

from playwright.sync_api import Page

from tetra import Library
from tetra.components import FormComponent

form_lib = Library("forms", "main")
ui = Library("ui", "main")


class SimpleTestForm1(Form):
    # a form with many different field types
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    address = forms.CharField()
    accept_terms = forms.BooleanField(required=True)
    count = forms.IntegerField()
    size = forms.FloatField()


def test_form_component_registration():
    """test FormComponent initialization and attribute assignment"""

    @form_lib.register
    class Foo(FormComponent):
        form_class = SimpleTestForm1
        template = """<div id="component"></div>"""


#     # TODO
# def test_recalculate_attrs_clears_errors():
#     @lib.register
#     class Foo(FormComponent):
#         form_class = SimpleTestForm1
#         template = """<div id="component"></div>"""
#
#     c = lib.components["foo"]
#     c.form_submitted = False
#
#     # Call the method
#     c.recalculate_attrs(component_method_finished=True)
#
#     # Assert that errors were cleared


class PersonForm(forms.Form):
    name = forms.CharField(max_length=100)
    age = forms.IntegerField()
    email = forms.EmailField()
    dob = forms.DateField()
    weight = forms.FloatField(required=False)
    website = forms.URLField(required=False)
    lucky = forms.BooleanField(required=False)


@ui.register
class PersonComponent(FormComponent):
    form_class = PersonForm

    # language=html
    template = """
    <div>
        {{ form.name }}
        {{ form.age }}
        {{ form.email }}
        {{ form.dob }}
        <button id="submit-button" @click="submit()">Submit</button>
    </div>
    """


def test_form_gains_form_attributes(tetra_request):
    """Confirm that the PersonComponent receives attributes from its associated form
    fields."""

    c = PersonComponent(tetra_request)
    assert hasattr(c, "name")
    assert hasattr(c, "age")
    assert hasattr(c, "email")
    assert hasattr(c, "dob")
    assert hasattr(c, "weight")
    assert hasattr(c, "website")
    assert hasattr(c, "lucky")


def test_form_knows_type_annotations(tetra_request):
    """Confirm that the PersonComponent receives attributes from its associated form
    fields."""

    c = PersonComponent(tetra_request)
    assert c.__annotations__["name"] == str
    assert c.__annotations__["age"] == int
    assert c.__annotations__["email"] == str
    assert c.__annotations__["dob"] == date
    assert c.__annotations__["weight"] == float
    assert c.__annotations__["website"] == str
    assert c.__annotations__["lucky"] == bool


class FormWithInitialData(forms.Form):
    name = forms.CharField(initial="John Doe")
    age = forms.IntegerField(initial=23)
    email = forms.EmailField(initial="john@example.com")
    dob = forms.DateField(initial=date(2000, 1, 1))
    weight = forms.FloatField(initial=70.5)
    website = forms.URLField(initial="https://example.com")
    lucky = forms.BooleanField(initial=True)


@ui.register
class ComponentWithInitialData(FormComponent):
    form_class = FormWithInitialData
    template = "<div></div>"


def test_form_initial_values(tetra_request):
    """Test that form fields are initialized with their initial values."""

    c = ComponentWithInitialData(tetra_request)
    assert c.name == "John Doe"  # noqa
    assert c.age == 23  # noqa
    assert c.email == "john@example.com"  # noqa
    assert c.dob == date(2000, 1, 1)  # noqa
    assert c.weight == 70.5  # noqa
    assert c.website == "https://example.com"  # noqa
    assert c.lucky == True  # noqa


def test_form_component_get_form(tetra_request):
    """Test that get_form() returns a properly initialized form."""

    c = ComponentWithInitialData(tetra_request)
    form = c.get_form()

    assert isinstance(form, FormWithInitialData)
    assert form.data == {
        "key": "main__ui__component_with_initial_data",
        "name": "John Doe",
        "age": 23,
        "email": "john@example.com",
        "dob": date(2000, 1, 1),
        "weight": 70.5,
        "website": "https://example.com",
        "lucky": True,
    }


@pytest.mark.playwright
def test_person_component_call_submit_triggers_form_valid(page: Page, live_server):

    with patch.object(PersonComponent, "form_valid") as mock_form_valid:
        # Navigate to upload element and add file
        page.goto(
            live_server.url
            + reverse("generic_ui_component_test_view", args=["PersonComponent"])
        )
        page.locator("#id_name").type("Johny Deo")
        page.locator("#id_age").type("21")
        page.locator("#id_email").type("john@example.net")
        page.locator("#id_dob").type("2000-01-02")
        # page.locator("#id_weight").type("70.0")
        # page.locator("#id_website").type("https://example.net")
        # page.locator("#id_lucky").check()

        page.locator("#submit-button").click()
        page.wait_for_load_state()

        mock_form_valid.assert_called_once()


@pytest.mark.playwright
def test_person_component_call_submit_triggers_form_invalid(page: Page, live_server):
    """
    Test that the PersonComponent form submission triggers form_invalid method
    for invalid data.
    """
    with patch.object(PersonComponent, "form_invalid") as mock_form_invalid:
        page.goto(
            live_server.url
            + reverse("generic_ui_component_test_view", args=["PersonComponent"])
        )
        page.locator("#id_name").type("John Doe")
        page.locator("#submit-button").click()
        page.wait_for_load_state()
        mock_form_invalid.assert_called_once()

    with patch.object(PersonComponent, "form_invalid") as mock_form_invalid:
        page.locator("#id_age").type("23")
        page.locator("#id_name").clear()
        page.locator("#submit-button").click()
        page.wait_for_load_state()
        mock_form_invalid.assert_called_once()
