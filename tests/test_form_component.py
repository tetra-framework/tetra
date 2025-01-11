import pytest
from django import forms
from django.forms import Form
from django.apps import apps

from tetra import Library
from tetra.components import FormComponent


class TestForm1(Form):
    # a form with many different field types
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    address = forms.CharField()
    accept_terms = forms.BooleanField(required=True)
    count = forms.IntegerField()
    size = forms.FloatField()


class Form1Component(FormComponent):
    form_class = TestForm1
    template = """<div id="component"></div>"""


@pytest.mark.django_db
def test_form_component():
    """Tests a simple component with a dict attribute"""
    app = apps.get_app_configs()
    lib = Library("default", app=apps.get_app_config("main"))
    lib.register(Form1Component)
    assert lib.components
    pass
    # assert (
    #     extract_component(content, innerHTML=True)
    #     == """<input id="id_first_name" maxlength="100" name="first_name" required="" type="text" value="John" x-model="first_name"/>"""
    # )
