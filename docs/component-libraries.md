---
title: Libraries
---

# Libraries

Every Tetra component belongs to a component library. Basically, libraries are the modules within `<myapp>.components` (or, alternatively, `<myapp>.tetra_components`) where components are found automatically:

```
myapp
├── components/
│      ├──anotherlib
│      ├──default *
│      ├──ui
```

With other words: The first module layer within `myapp.components` are libraries. It doesn't matter if you create libraries as file modules, or packages, both are equally used, with one difference: package modules allow [Directory style components](#directory-style-components), see below.

When resolving a component, and you don't specify a library in your *component tag*, Tetra assumes you put the component in the `default` library. However, you can have infinite libraries. This is a good way to organise components into related sets. Each library's Javascript and CSS is packaged together. As long as components are registered to a library and that library instance is available in `<myapp>.components` or `<myapp>.tetra_components` they will be available to use from templates, and within other components.

While it is not necessary, it is also possible to create libraries manually (e.g. in your testing files). You have to provide a `name` and an `app`, and if the same library was already registered, it is not recreated - the library with that name is reused, so name and app are unique together within libraries.

```python
from tetra import Library, Component
from django.apps import apps

class FooComponent(Component):
    template = "<div>foo!</div>"

# create a new library named "default" for the "main" app
default = Library(name="default", app=apps.get_app_config("main"))

# register the FooComponent manually to the default library
default.register(FooComponent)

# if you create a library twice, or you use a library that was already created automatically by
# creating a "default" folder in your `<myapp>.components` directory, that library is reused.
# Here, default is the same object as default_double:
default_double = Library("default", "main")
```

#### Directory style components
A component is created as a subclass of `BasicComponent` or `Component` and registered to a library by placing it into the library package. Let's see how the directory structure would look like for a `MyCalendar` component:

```
myapp
├── components/
│    │   └──default
│    │       └── my_calendar/
│    │           ├──__init__.py*  <-- here is the component class defined
│    │           ├──script.js
│    │           ├──style.css
│    │           └──my_calendar.html*
```

The `__init__.py` and `my_calendar.html` template are mandatory, css/js and other files are optional.

#### Inline components

There is another (shortcut) way of creating components, especially for simple building bricks (like `BasicComponents` without Js, CSS, and with small HTML templates).
Create a component class and place it directly into a library module. You can create multiple components directly in the module. The simplest form is directly in the `default` library:
``` python
#myapp/components/default.py

class Link(BasicComponent):
    href: str = ""
    title: str = ""
    template: django_html = "<a href='{{href}}'>{{title}}</a> 
```

However, You can mix directory libraries and file libraries as you want: Put a few components into `default/__init__.py`, and another into `default/my_component/__init__.py`. Both are found:

```
myapp
├── components/
│   │   ├──default
│   │   │   └──__init__.py   <-- put all "default" component classes in here
│   │   ├──otherlib.py       <-- put all "otherlib" component classes in here
│   │   ├──widgets
│   │   │   ├──__init__.py   <-- put all "widgets" component classes in here
│   │   │   ├──link
│   │   │   │   ├──__init__.py  <-- Link component definition
│   │   │   │   └──link.html
    ...
```



!!! note
    If you use a **directory style component**, make sure you define only ONE component class per module (e.g. in `components/default/my_calendar.py`). If you use the library module directly to create components (`components/default.py`), you can certainly put multiple components in there.

## Manually declared libraries

It is not necessary to follow the directory structure. You can also declare a Library anywhere in your code, and register components to it. The `Library` class takes the *name of the library* and the *AppConfig (or app label)* as parameters. You can declare the libraries more than once, everything with the same name/app will be merged together.

```python
from tetra import Library

widgets = Library("widgets", "ui")
# this is the same library!
widgets_too = Library("widgets", "ui")
```

When a Library is declared, you can register Components to it by using the `@<library>.register` decorator:

```python
@widgets.register
class Button(BasicComponent):
    ...
```

As a decorator can be used as a function, you can even register components in code:

```python
lib = Library("mylib", "myapp")
lib.register(MyComponentClass)
```