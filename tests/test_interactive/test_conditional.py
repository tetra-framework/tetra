import pytest
from django import forms
from django.urls import reverse
from playwright.sync_api import Page

from tetra import Library, public
from tetra.components import FormComponent, DynamicFormMixin

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
class CarModelComponent(DynamicFormMixin, FormComponent):
    form_class = ConditionalForm

    @public.watch("vendor")
    def vendor_changed(self, value, old_value, attr):
        pass

    def get_model_choices(self):
        vendor = self.vendor
        if not vendor:
            return ()

        return ((f"{vendor}_{model.lower()}", model) for model in car_models[vendor])

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
def test_conditional_form_component(component_locator):
    """
    Test that the ConditionalFormComponent updates the model choices based on the
    selected vendor.
    """

    component = component_locator(CarModelComponent)

    # Select Volvo
    component.locator("#id_vendor").select_option("volvo")
    component.locator("#id_model").select_option("volvo_v40")

    model_options = component.locator("#id_model option").all_text_contents()
    assert "V40" in model_options
    assert "V60" in model_options
    assert "S60" in model_options
    assert "S80" in model_options

    # Select VW
    component.locator("#id_vendor").select_option("vw")

    # Wait for the model dropdown to be populated with VW options
    # Wait specifically for a VW option to appear (not a Volvo option)
    component.locator("#id_model option:has-text('Golf')").wait_for(state="attached")

    # Check that the model choices are updated to VW models
    model_options = component.locator("#id_model option").all_text_contents()
    assert "Golf" in model_options
    assert "Polo" in model_options
    assert "Passat" in model_options
