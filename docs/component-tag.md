---
title: The `component` Tag
--- 

# The `component` Tag

Tetra components are included in a template with the `component` template tag, e.g. for a `Button` component in your `ui` library:
```django
{% component ui.Button %}
```

For your convenience, and to reduce verbosity, you can even omit "component" and write the component class name itself as tag:

```django
{% ui.Button %}
```
!!! note
    The direct `library.ClassName` tag is the recommended usage, and we will use it in our examples too, without the `component` prefix.

If you omit the library namespace, the "default" library is assumed, e.g. for `default.Calendar`:

```django
{% Calendar / %}
```
This renders the Calendar component of the default library. It does not matter, in which app you declared it,
Tetra finds the component automatically. If there are two `Calendar` components in different apps, Tetra uses the first 
available, like Django does in templates.

The component tag (and hence all components as tags themselves) are automatically available in your components' inner templates. 
In Django templates ensure to `{% load tetra %}`.

You maybe saw the ending "/": Unlike most Django template tags, the `component` tag can optionally be "open" accepting 
content, or "closed". To indicate that it is 'closed' it should end with a forward slash `/` such as:

``` django
{% Calendar / %}
```

An open tag with content in between must be closed with a `{% /<ComponentName> %}` tag:

``` django
{% Calendar %}
  Some content
{% /Calendar %}
```

!!! note
    Since v0.1.2, Tetra uses PascalCase component references in templates, to match the class name - this helps you 
    finding components and its usages during coding in your IDE, as the class name is exactly the same string.
    As legacy feature, you can also use the `snake_case_name` to reference your component, but this may be removed
    in a future version.

## Resolving components

All components belong to a component library, which basicalyl "belong" to a "Django App" - but are overlapping apps. 
You can specify a component as either:

  - `ComponentName`

    When you specify only the component name, Tetra attempts to resolve the component **in the `default` library** (of any app).

  - `library_name.ComponentName`

    No matter in which app the component is declared, if the app declared in "library_name", Tetra finds it.


## Dynamically resolved component names

Sometimes you want to determine the component name at runtime, e.g. when the components are part of a plugin system, 
or when you render components in a for loop. Tetra allows you to determine the component name at runtime. 
You have to explicitly use `component` as tag here, and place a `=` character before the variable name:

```django
{% for component in components %}
    {% component =component /%}
{% endfor %}
```

!!! note
    Due to their undetermined nature, Tetra is not able to save dynamic components' states. 
    Hence, **dynamic components are always rendered using their initial state** when loaded in the template, 
    see more at [Component life cycle][component-life-cycle.md] about that 
    However, their state is saved within the component itself, so if the component reacts to an inside event (e.g. a button click *in* the component), the state is certainly saved and reused.

## Passing Arguments

Both positional and keyword arguments can be passed to a component via the `@` tag. These are passed to the `load` method of the component:

``` python
class MyComponent(Component):
    ...
    def load(self, a_var, something=None, another=False, *args, **kwargs):
        ...
```

``` django
{% MyComponent "a string" something=123 another=value_of_a_context_var / %}
```

Your components `load` methods can accept any number of optional positional and keyword arguments by using `*args` and `**kwargs`.

## Passing HTML Attributes

It is common to want to set HTML attributes on the root element of your component - this can be done with the `attrs:` label, followed by a space-separated list of `key=value` pairs, with the "key" being the name of the attribute. The value can be a context variable that will be resolved when rendering.

``` django
{% MyComponent attrs: class="my-class" style="font-wight:bold;" / %}
```

These are made available as `attrs` in the component's template, the [attribute  `...` tag](attribute-tag.md) should be used to unpack them into the root tag, its [docs](attribute-tag.md) details how this works.

## Passing Context

By default, outer template context is not passed down to the component's template when rendering; this is to optimise the size of the saved component state. You can explicitly pass context to a component with the `context:` label, followed by a space-separated list of either variable names or `key=value` pairs, where the "key" will be the new name for a context var, and the value either a variable name or a literal.

``` django
{% MyComponent context: a_context_var something=old_name another="a string" / %}
```

It is also possible to explicitly pass all template context to a component with the `__all__` argument:

``` django
{% MyComponent context: __all__ / %}
```

!!! warning
    This should be used sparingly as the whole template context will be saved with the component's saved (encrypted) state, and sent to the client, see [state security](state-security.md).

In general, if the value is something that is needed for the component to function (and be available to methods or be "public") it should be generally passed as an *argument* [(see above)](#passing-attributes). Passing context is ideal for composing your components with inner content passed down from an outer template (see [passing slots](slots.md)).

When context is passed using the `_extra_context` class attribute, you can always override these variables in the component tag:

``` django
{{ var }} {# this is "5" #}
{% MyComponent context: var=3 / %} {# overrides global var with "3" #}
```
 