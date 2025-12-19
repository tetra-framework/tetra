from django.forms import Form
from django import forms

from tetra.components import FormComponent


class PersonForm(Form):
    first_name = forms.CharField(max_length=100, initial="John")


class SimpleFormComponent(FormComponent):
    form_class = PersonForm
    template = """<div id="component">{{ form.first_name }}</div>"""
