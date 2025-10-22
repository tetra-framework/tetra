import pytest
from unittest.mock import patch
from django import forms
from django.urls import reverse
from playwright.sync_api import Page
from tetra import Library
from tetra.components import FormComponent

ui = Library("ui", "main")


class PersonForm(forms.Form):
    name = forms.CharField(max_length=100)
    age = forms.IntegerField()


@ui.register
class PersonComponent1(FormComponent):
    form_class = PersonForm

    # language=html
    template = """
    <div>
        {{ form.name }}
        {{ form.age }}
        <button id="submit-button" @click="submit()">Submit</button>
    </div>
    """


def test_form_gains_form_attributes(tetra_request):
    """Confirm that the PersonComponent1 receives attributes from its associated form
    fields."""

    c = PersonComponent1(tetra_request)
    assert hasattr(c, "name")
    assert hasattr(c, "age")


@pytest.mark.playwright
def test_person_component_call_submit_valid(page: Page, live_server):
    """Test that the PersonComponent1 form submission triggers the form_valid method."""

    with patch.object(PersonComponent1, "form_valid") as mock_form_valid:
        # Navigate to upload element and add file
        page.goto(
            live_server.url
            + reverse("generic_ui_component_test_view", args=["PersonComponent1"])
        )
        page.locator("#id_name").type("John Doe")
        page.locator("#id_age").type("23")

        page.locator("#submit-button").click()
        page.wait_for_load_state()

        mock_form_valid.assert_called_once()


@pytest.mark.playwright
def test_person_component_call_submit_invalid(page: Page, live_server):
    """
    Test that the PersonComponent1 form submission triggers form_invalid method
    for invalid data.
    """
    with patch.object(PersonComponent1, "form_invalid") as mock_form_invalid:
        # Navigate to upload element and add file
        page.goto(
            live_server.url
            + reverse("generic_ui_component_test_view", args=["PersonComponent1"])
        )
        page.locator("#id_name").type("John Doe")
        page.locator("#submit-button").click()
        page.wait_for_load_state()
        mock_form_invalid.assert_called_once()

    with patch.object(PersonComponent1, "form_invalid") as mock_form_invalid:
        page.locator("#id_age").type("23")
        page.locator("#id_name").clear()
        page.locator("#submit-button").click()
        page.wait_for_load_state()
        mock_form_invalid.assert_called_once()
