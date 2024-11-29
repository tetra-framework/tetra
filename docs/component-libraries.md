---
title: Libraries
---

# Component Libraries

Every Tetra component belongs to a component library. Your component libraries are found automatically as packages within `<yourapp>.components` (or, alternatively, `<yourapp>.tetra_components`):

```
myapp
├── components/
│      ├──anotherlib
│      ├──default *
│      ├──ui
```

The first module layer within `components` are libraries. It doesn't matter if you create libraries as file modules, or packages, both are equally used, with one difference: package modules allow components-as-directories, see below.

When resolving a component, and you don't specify a library in your component tag, Tetra assumes you put the component in the `default` library. However, you can have infinite libraries. This is a good way to organise components into related sets. Each library's JS and CSS is packaged together. As long as components are registered to a library and that library instance is available in `<yourapp>.components` or `<yourapp>.tetra_components` they will be available to use from templates, and within other components.

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

There is another (shortcut) way of creating components, especially for simple building bricks (like BasicComponents without Js):
Create a component class and place it directly into a library module. You can create multiple components directly in the module.
```
myapp
├── components/
│   │   ├──default
│   │   │   └──__init__.py   <-- put all "default" component classes in here
│   │   ├──otherlib.py       <-- put all "otherlib" component classes in here
│   │   ├──widgets
│   │   │   ├──__init__.py   <-- put all "widgets" component classes in here
    ...
```

You can mix directory libraries and file libraries as you want: Put a few components into `default/__init__.py`, and another into `default/my_component/__init__.py`. Both are found.

!!! note
    If you use a directory style component, make sure you only define ONE component class within the component's module (e.g. in `components/default/my_calendar/__init__.py`). If you use