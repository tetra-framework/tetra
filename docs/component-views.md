---
title: Components as Views
---

# Component Views

The `ViewMixin` allows you to use a Tetra component as a standalone Django view. This is useful when you want 
a component to be the main content of a page, accessible directly via a URL.

Standalone component views only support `GET` requests, as they are intended to load the initial state of the component.
Once rendered, the component functions as a normal Tetra component.

## Usage

To create a component view, inherit from `ViewMixin` in addition to `Component` or `BasicComponent`.

```python
# components/some_lib/greeter_component/__init__.py
from tetra import Component, ViewMixin


class GreeterComponent(ViewMixin, Component):
    allowed_params = ["name"]
    template = "<div>Hello {{ name }}</div>"

    def load(self, name="World"):
        self.name = name
```

## URL Configuration

Components with the `ViewMixin` are registered as normal Tetra components. Additionally, they behave like any 
other Class-Based-View. You can use them with their `as_view()` method to include it in your `urls.py`.

```python
# urls.py
from django.urls import path
from .components import GreeterComponent

urlpatterns = [
    path('hello/', GreeterComponent.as_view()),
    path('hello/?name=Tetra', GreeterComponent.as_view()),
]
```

## Passing Parameters

Parameters can be passed to the component's `load()` method in two ways:

**as_view() params**

### Query parameters

Any query parameters from the URL are passed directly to `load()`.

If you visit `/hello/?name=Tetra`, the component will be initialized with `name="Tetra"` and the `name` parameter will be passed to `load(name="Tetra")`.

To prevent accidentally overriding parameters by the URL, query parameters are ignored by default. To allow them, add params to the `allowed_params` list in your component:

```python
class GreeterComponent(ViewMixin, Component):
    allowed_params = ["name"]
    template = "<div>{{ greeting }}, {{ name }}</div>"

    def load(selfself, name:str, age:int=None):
        if age:
            if age < 20:
                self.greeting = "Hi"
            else:
                self.greeting = "Good day"
        self.name = name

```

### as_view() parameters
Any keyword params directly passed to `as_view()` are passed to `load()` without modification. 

```python
# urls.py
urlpatterns = [
    path('hello/', GreeterComponent.as_view(name="Frank")),
]
```

Note that query parameters always take precedence over `as_view()` parameters.


## Limitations

*   **GET only**: `ViewMixin` only supports `GET` requests. It returns a `405 Method Not Allowed` response for other HTTP methods.
*   **Initial Load**: It is designed for the initial page load. Subsequent interactions with the component (e.g., public method calls) are handled by Tetra's standard mechanisms (XHR or WewbSockets).
