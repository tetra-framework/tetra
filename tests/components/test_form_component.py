import pytest
from datetime import date
from unittest.mock import patch

from django import forms
from django.forms import Form
from django.urls import reverse

from typing import Optional
from playwright.sync_api import Page, expect

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
    # Form fields should always be Optional because they can be None
    # or empty initially, and Django's form validation handles the
    # "required" check, not the component state.

    c = PersonComponent(tetra_request)
    assert c.__annotations__["name"] == Optional[str]
    assert c.__annotations__["age"] == Optional[int]
    assert c.__annotations__["email"] == Optional[str]
    assert c.__annotations__["dob"] == Optional[date]
    assert c.__annotations__["weight"] == Optional[float]
    assert c.__annotations__["website"] == Optional[str]
    assert c.__annotations__["lucky"] == Optional[bool]


def test_component_subclass_has_own_annotations_dict():
    """Every Component subclass must have its own __annotations__ dict (not inherited).

    Without this guarantee, cls.__annotations__ on a class with no annotated
    attributes would silently return a parent class's dict, causing annotation
    lookups to find wrong or missing entries.
    """

    class MyBareComponent(FormComponent):
        form_class = PersonForm
        template = "<div></div>"

    # The class must own its annotations dict, not inherit it.
    assert "__annotations__" in MyBareComponent.__dict__
    # And it must not be the same object as any parent's dict.
    for parent in MyBareComponent.__mro__[1:]:
        assert MyBareComponent.__dict__["__annotations__"] is not parent.__dict__.get(
            "__annotations__"
        )


def test_form_subclass_annotations_found_via_mro(tetra_request):
    """Annotations from a parent FormComponent are accessible through the MRO in
    subclasses that do not re-declare form_class.

    This tests fixes for:
    - _init_component_class using type(cls).__annotations__ (metaclass level)
    - _resume_component_state and _get_validation_data only checking the direct
      class's own __annotations__ instead of searching the full MRO.
    """

    @ui.register
    class SubPersonComponent(PersonComponent):
        template = "<div></div>"

    sub = SubPersonComponent(tetra_request)

    # SubPersonComponent has no form_class of its own, so its own __annotations__
    # should not contain the form fields.
    assert "name" not in sub.__class__.__dict__["__annotations__"]

    # Merging the MRO (the pattern used by the fixed methods) must find them.
    merged = {}
    for klass in type(sub).__mro__:
        if hasattr(klass, "__annotations__"):
            for k, v in klass.__annotations__.items():
                if k not in merged:  # most-derived wins
                    merged[k] = v

    assert merged.get("name") == Optional[str]
    assert merged.get("age") == Optional[int]
    assert merged.get("dob") == Optional[date]


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
    assert form.data["key"].startswith("tk_")
    assert {k: v for k, v in form.data.items() if k != "key"} == {
        "name": "John Doe",
        "age": 23,
        "email": "john@example.com",
        "dob": date(2000, 1, 1),
        "weight": 70.5,
        "website": "https://example.com",
        "lucky": True,
    }


@pytest.mark.playwright
def test_person_component_call_submit_triggers_form_valid(
    page: Page, component_locator
):
    """Test that the PersonComponent form submission triggers form_valid method
    for valid data."""

    with patch.object(PersonComponent, "form_valid") as mock_form_valid:
        component = component_locator(PersonComponent)

        component.locator("#id_name").wait_for(state="visible")
        component.locator("#id_name").fill("John Doe")
        component.locator("#id_age").fill("23")
        component.locator("#id_email").fill("john@example.net")
        component.locator("#id_dob").fill("2000-01-02")

        component.locator("#submit-button").click()

        # Wait for network to be idle after the click
        page.wait_for_load_state("networkidle")

        mock_form_valid.assert_called_once()


@pytest.mark.playwright
def test_person_component_call_submit_triggers_form_invalid(
    page: Page, component_locator
):
    """
    Test that the PersonComponent form submission triggers form_invalid method
    for invalid data.
    """
    with patch.object(PersonComponent, "form_invalid") as mock_form_invalid:
        component = component_locator(PersonComponent)
        component.locator("#id_name").fill("John Doe")
        component.locator("#submit-button").click()

        # Wait for network to be idle after the click
        page.wait_for_load_state("networkidle")

        mock_form_invalid.assert_called_once()

    with patch.object(PersonComponent, "form_invalid") as mock_form_invalid:
        component = component_locator(PersonComponent)
        component.locator("#id_age").fill("23")
        component.locator("#id_name").clear()
        component.locator("#submit-button").click()

        # Wait for network to be idle after the click
        page.wait_for_load_state("networkidle")

        mock_form_invalid.assert_called_once()
