---
title: Form components
---

# Form components

Tetra provides a `FormComponent` class that encapsules basic Django form handling. Django forms support validation, 
and can easily add some basic cleaning logic.
Public attributes are automatically created for all form fields, so you don't have to declare them manually again.

!!! note
    <p>Tetra does not encourage using `<form>` tags and form submits for each input element. You don't need form tags at all.
    Best practice would be to only use `<form>` tags only if you actually build a form. If you just need an e.g. input
    field which acts as a search field and triggers a component refresh, don't use a `<form>` tag.
    </p>
    <p>What is meant with "Form support" is [Django forms](https://docs.djangoproject.com/en/5.0/topics/forms/)</p

The FormComponent is easy to use. First, create a normal Django form (Form, ModelForm, etc.):

```python
from tetra.components.base import FormComponent, public
from tetra.library import Library
from django import forms 

class PersonForm(forms.Form):
    first_name = forms.CharField(max_length=25, initial="Jean-Luc")
    last_name = forms.CharField(max_length=25, initial="Picard")

default=Library()

@default.register
class PersonFormEditor(FormComponent):
    form_class = PersonForm
    is_editing = public(False)
```

Tetra automatically creates the needed public fields in PersonFormEditor from the PersonForm, so you don't have to
write them manually.
```python
    first_name = public("Jean-Luc")
    last_name = public("Picard")
```

In a `FormComponent`, the form is instantiated automatically each time the component is loaded or updated
.
## ModelForm components
Tetra provides you with a convenient form component named `GenericObjectFormComponent` that represents a Django model.

```python
# models.py
from django.db import models

class Person(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
```

```python
# forms.py
from django.forms import ModelForm
from .models import Person


class PersonForm(ModelForm):
    class Meta:
        model=Person
    
    # you can use any form validation/cleaning as usual
    def clean_last_name(self):
        return self.cleaned_data["last_name"].upper()

```

```python
# components.py
from tetra.components.base import GenericObjectFormComponent, public
from .models import Person
from .forms import PersonForm


class PersonEditor(GenericObjectFormComponent):
    form_class = PersonForm
    object: Person = None

    # define other attributes as you need them
    is_editing = public(False)
    
    template = """..."""
```
With a `GenericObjectFormComponent`, you just have to define the `form_class` and object, everything else does Tetra 
for you, like Django's `UpdateView`.

## Form processing and usage

### Frontend

Tetra will automatically take care of all the form fields and expose them to the frontend in Javascript/Alpine.js. You 
can automatically use those fields in your frontend:

```html
<input type="text" x-model="first_name">
```

!!! warning
    **All fields of the form class are exposed to the frontend!** Make absolutely sure that no sensible data will be 
    exposed this way. You can always control which fields are used by Django's `Form.Meta.fields` list.

### Backend

In the backend, all public attributes are synchronized automatically as usual. When using the form, you can always get 
an instanciated form with the current data using `self.get_form()`

### Form validation

You can use Django's form validation at any point in the backend using two different ways:

You can validate the form in the backend anytime using `self.validate()`. This will instantiate a `form_class()` with the 
current data of the frontend and validate it. It will add form errors to the `form_errors` attribute,
so you can render this data in your component as Django template variable `{{ form_errors }}`.

The `validate()` method is also exposed to the frontend, so you can call it from there using Alpine's `@click` attribute:

```html
<button @click="validate()">Check</button>
```


### Submission

To submit a form using Javascript, use `submit()` in the frontend. This will (similarly to UpdateView's post()) submit the
form, including validating it. If the form is valid, the component's `form_valid()` method is called in the backend.
If it is invalid, `form_invalid()` is called. You can place code in those functions (alike Django's views) to react on 
successful/unsuccessful form submission.

```html
<button type="submit" @click.prevent="submit()">Check</button>
```

Here, `@click.prevent` is used to prevent the Browser submitting the form the usual way.


### Resetting the form

You can reset the form to its default values by calling `reset()`, from the frontend, or the backend.

### File uploading

It is a fact that HTML forms traditionally have some problems with files, as they are designed around the *submit -> POST-request -> response -> full-page-reload* cycle. This works, as long as after the submission, the server saves the file. If the form does not validate correctly (e.g. some unfilled input field), Django renders the form again using a GET request. And here HTML (for security reasons) does not add the file again to the form. So with the next submit, the file field is empty again. This is not solvable with normal Django tools.

Tetra finds a solution to that problem within FormComponent. When you use a FileField in a Django Form, FormComponent makes sure that when the user adds a file to the field, it is instantly uploaded to the server, and saved as a temporary file. After submitting the FormComponent, when validation succeeds, the file is simply moved to its target position. This all works transparently in the background.

Just keep in mind, that the file is **uploaded already at the `@change` event** of the file field.