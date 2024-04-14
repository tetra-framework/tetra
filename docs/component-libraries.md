---
title: Libraries
---

# Component Libraries

Every Tetra component belongs to a component library. When resolving a component your apps `default` library is checked first, however, you can have infinite libraries. This is a good way to organise components into related sets. Each library's JS and CSS is packaged together.

Your component libraries are found in `yourapp.components` or `yourapp.tetra_components`, this can be a module or package.

If you are creating many components you will likely want to split them between multiple files. As long as they are registered to a library and that library instance is available in `yourapp.components` or `yourapp.tetra_components` they will be available to use from templates, and within other components.

``` python
# yourapp/components.py
from tetra import Library, Component, BasicComponent

default = Library()
anotherlib = Library()
```

A component is created as a subclass of `BasicComponent` or `Component` and registered to a library with the `@libraryname.register` decorator.

``` python
@default.register
class MyComponent(Component):
    ...
```

As standard, the component's name is converted from the "CamelCase" class name to "snake_case". You can provide your own component name to the register decorator.

``` python
@anotherlib.register(name="my_other_component")
class AnotherComponent(Component):
    ...
```

## Splitting up component files

You may find that when you have multiple components and component libraries you will want to split the files up to organise them better. As noted above, as long as your `Library` instances are in `yourapp.components` or `yourapp.tetra_components` you can place the components anywhere. However, this is the recommended way to organise them:

With a `components` package, your `__init__.py` needs to have all your `Library` instances imported and available:

``` python
# components/__init__.py
from .default import default
from .my_components import my_components
```
    
You can then define your component libraries in other modules. Best practice is to name your module/package the same as the component library:

``` python
# components/default.py
from tetra import Library, Component

default = Library()
...
```

Component libraries can be split across multiple files. Define the library instance in a `base.py` file within a module with the same name as your library:

``` python
# components/my_components/base.py
from tetra import Library, Component

my_components = Library()
...
```

Then import the library instance into other modules, and register your components there. For larger components you may want to have a single file per component:

``` python
# components/my_components/a_component.py
from tetra import Component, BasicComponent
from .base import my_components

@my_components.register
class AComponent(Component):
    ...
```

You must ensure that all modules that register components are imported into your packages `__init__.py`:

``` python
# components/my_components/__init__.py
from .base import my_components
from .a_component import *
from .another_module import *
```