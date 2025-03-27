import pytest
from django import forms
from django.forms import Form

from tetra import Library
from tetra.components import FormComponent

lib = Library("forms", "main")


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

    @lib.register
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
