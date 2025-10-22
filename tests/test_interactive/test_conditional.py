import pytest
from django import forms
from django.urls import reverse
from playwright.sync_api import Page

from tetra import Library, public
from tetra.components import FormComponent

ui = Library("ui", "main")

car_models = {
    "vw": ["Golf", "Polo", "Passat"],
    "volvo": ["V40", "V60", "S60", "S80"],
}


class ConditionalForm(forms.Form):

    vendor = forms.ChoiceField(choices=[("volvo", "Volvo"), ("vw", "Volkswagen")])
    model = forms.ChoiceField()
    year = forms.IntegerField(required=False)


@ui.register
class CarModelComponent(FormComponent):
    form_class = ConditionalForm

    @public.watch("vendor")
    def vendor_changed(self, value, old_value, attr):
        self.form.fields["model"].choices = [
            (f"{value}_{model}", f"{model.capitalize()} {value.capitalize()}")
            for model in car_models[value]
        ]

    # language=html
    template = """
    <div>
        {{ form.vendor }}
        {{ form.model }}
        {{ form.year }}
        <div id="errors">{{ form.file.errors }}</div>
        <button id="submit-button" @click="submit()">Save</button>
        <div id="result">{{ text }}</div>
    </div>
    """


@pytest.mark.playwright
def test_conditional_form_component(page: Page, live_server):
    """
    Test that the ConditionalFormComponent updates the model choices based on the
    selected vendor.
    """

    page.goto(
        live_server.url
        + reverse("generic_ui_component_test_view", args=["CarModelComponent"])
    )

    # Select Volvo
    page.locator("#id_vendor").select_option("volvo")
    page.wait_for_load_state()
    page.locator("#id_model").select_option("volvo_v40")

    # Check that the model choices are updated
    assert page.locator("#id_model").has_option("Volvo V40")
    assert page.locator("#id_model").has_option("Volvo Polo")
    assert page.locator("#id_model").has_option("Volvo Passat")

    # Select VW
    page.locator("#id_vendor").select_option("vw")
