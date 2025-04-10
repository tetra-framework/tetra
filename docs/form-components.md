---
title: Form components
---

# Form components

Tetra provides a `FormComponent` class that encapsules basic Django form handling. Django forms support validation, 
and can easily add some basic cleaning logic.
Public attributes are automatically created for all form fields, so you don't have to declare them manually again.

!!! note
    <p>Tetra does not encourage using `<form>` tags and form submits for each input element. You don't need form tags at all. It creates a FormData object on the fly when uploading data.
    Best practice would be to only use `<form>` tags only if you actually build a *form* that needs to be non-Javascript compatible.
    </p>
    <p>What is meant with "Form support" is [Django forms](https://docs.djangoproject.com/en/5.0/topics/forms/)</p

The FormComponent is easy to use. First, create a normal Django form (Form, ModelForm, etc.), and a FormComponent that uses that form:

```python
# components/default.py
from tetra.components.base import FormComponent, public
from django import forms 

class PersonForm(forms.Form):
    first_name = forms.CharField(max_length=25, initial="Jean-Luc")
    last_name = forms.CharField(max_length=25, initial="Picard")

class PersonFormEditor(FormComponent):
    form_class = PersonForm

    # Tetra automatically creates these fields for you:
    # first_name = public("Jean-Luc")
    # last_name = public("Picard")
```

Tetra automatically creates component attributes from Form fields and keeps them in sync. 
In a `FormComponent`, the form itself is also instantiated automatically each time the component is loaded or updated. You can use `self._form` in backend methods. In the HTML template, the form is available as `{{ form }}` as usual in Django, this is even possible with e.g. [Crispy Forms](https://github.com/django-crispy-forms/django-crispy-forms):

```django
{{ form.first_name | as_crispy_field }}
```

## ModelForm components
Another convenient form component is `ModelFormComponent` that supports a Django model directly:

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
from tetra.components.base import ModelFormComponent, public
from .models import Person
from .forms import PersonForm


class PersonEditor(ModelFormComponent):
    form_class = PersonForm
    object: Person = None

    # define other attributes as you need them
    is_editing = public(False)

    template = """..."""
```
With a `ModelFormComponent`, as minimum you have to define the `form_class` and `object`, everything else does Tetra for you, like Django's `UpdateView`.

## Form processing and usage

### Frontend

Tetra will automatically take care of all the form fields and expose them to the frontend in Javascript/Alpine.js. You can automatically use those fields in your frontend:

```html
<input type="text" x-model="first_name">
```

You can use the variables as usual in your html code. 

Normal Django variables are only changed after the component is reloaded:

```django
<div>{{ first_name }}</div>
```

If you want to use frontend variables, you can use the `@v` tag helper. In this case, a `<span>` tag is created with the `first_name` content that will reflect the variable instantly.

```django
<input type="text" x-model="first_name">
<div>{% @v "first_name" %} is a good name!</div>
```


### Backend

In the backend, all public attributes are synchronized automatically as usual. When using the form, you can always get 
an instanciated form with the current data using `self.get_form()`

### Security concerns

!!! warning
    **All fields of the form class are exposed to the frontend!** Make absolutely sure that no sensible data will be exposed this way. You can always control which fields are used by Django's `Form.Meta.fields` list.

### Form validation

You can use Django's form validation at any point in the backend using two different ways:

You can validate the form in the backend anytime using `self.validate()`. This will use the form's validators. It will add form errors to the component's `form_errors` JSON attribute,
so you can render this data in your component as Django template variable `{% for error in  form_errors %}...`.

The `validate()` method is also exposed to the frontend, so you can call it from there using Alpine's `@click` attribute:

```html
<button @click="validate()">Check</button>
```


### Submission

To submit a form using Javascript, use `submit()` in the frontend. This will (similarly to UpdateView's `post()`) submit the form, including validating it. If the form is valid, your component's `form_valid()` method is called in the backend.
If it is invalid, `form_invalid()` is called. You can place code in those functions (alike Django's views) to react on successful/unsuccessful form submission.

```html
<button type="submit" @click.prevent="submit()">Check</button>
```

Here, `@click.prevent` is used to prevent the Browser submitting the form the usual way. If you don't place the button in a form, you don't have to use `.prevent`.

A helpful hint is to deactivate the button right after clicking it, to prevent users from double-clicking the button: disable it right after the click. You can use Alpine.js' `$el` property for that, before calling `submit()`:

```html
<button type="submit" @click="$el.disabled = true; submit()">Submit</button>
```


### Resetting a form

You can reset the form to its default values by calling `reset()`, from the frontend, or the backend.

### File uploading

It is a fact that HTML forms traditionally have some problems with files, as they are designed around the `submit -> POST-request -> response -> full-page-reload` cycle. This works, as long as after the submission, the server saves the file. If the form does not validate correctly (e.g. some unfilled input field), Django renders the form again using a GET request. And here (for security reasons) HTML does not add the file again to the form. So with the next submit, the file field is empty again. This is not solvable with normal Django tools.

Tetra provides a solution to that problem within FormComponent. When you use a FileField in a Django Form, FormComponent makes sure that when the form component is submitted (or any other POST request occurs using a component_method, even event-triggered!), the file is saved temporarily and a reference kept within the state. After successfully validating/saving the FormComponent, the file is moved to its target destination automatically.

If you want to change the location where Tetra uploads files temporarily, change the [TETRA_TEMP_UPLOAD_PATH](settings.md#tetra_temp_upload_path) setting.

Just keep in mind, that the file is already **uploaded at the first POST request**.


### Dynamically dependent fields

It is common that fields' values change dependent on another field's value. This is a common dilemma in Django and usually only can be solved using small chunks of Javascript that are sprinkled all over the client form. Tetra solves this problem smoothly by providing hook methods to dynamically update form fields. Have a look at this example:

```python
# models.py
class Make(models.Model):
    name = models.CharField(max_length=255)

class EngineType(models.Model):
    name = models.CharField(max_length=50)
    
class CarModel(models.Model):
    make = models.ForeignKey(on_delete=models.CASCADE)
    name = models.CharField
    

# forms.py
from django.forms import forms
class CarForm(forms.Form):
    make = forms.ChoiceField()
    model = forms.ChoiceField()
        
# components/default.py
class CarComponent(DependencyFormMixin, FormComponent):
    @þublic.watch("make")
    def make_changed(self, value, old_value, attr):
        """A dummy trigger hook, to rerender the component every time 'make' changes."""
    
    # these methods are called automagically when needed:
    def get_model_queryset(self) -> QuerySet[CarModel]:
        return CarModel.objects.filter(make=self.make)

    def get_engine_type_queryset(self) -> QuerySet[EngineType]:
        if self.make == Make.obejcts.get(name="Tesla"):
            return EngineType.objects.filter(name="Electric")
        return EngineType.objects.all()
    
    def get_engine_type_disabled(self) -> bool:
        # disable changing of engine type if brand == Tesla.
        return self.make == Make.obejcts.get(name="Tesla")
```

Tetra makes sure that whenever the form is rendered, the `queryset` and `disabled` attributes of the `model` or `engine_type` fields are changed updated based on the selection made in the `make` field.

You have to do two things:

1. Make sure that whenever a parent field value changes, the form is reloaded usign Tetra. Just use an empty dummy method and decorate it with `@public("<field>"")`
2. Create methods that are named using the scheme that Django also uses for `Form.clean_<field>()`. You have full access to all component methods and attributes in those methods:

###### `get_<field:T>_queryset(self)-> QuerySet[T]`

Return a `QuerySet` for that field that is valid for the current state of the component. 

###### `get_<field>_disabled(self) -> bool`

Determines whether a specific field should be dynamically **disabled** based on the current state of the component.

###### `get_<field>_hidden(self) -> bool`

Determines whether a specific field should be dynamically **hidden** based on the current state of the component.

###### `get_<field>_required(self) -> bool`

Determines whether a specific field should be dynamically **required** based on the current state of the component.

