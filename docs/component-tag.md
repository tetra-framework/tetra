---
title: The `@` Component Tag
---

# `@` Component Tag

Tetra components are included in a template with the `{% @ <component name> %}` template tag.

The component tag is automatically available in your components' templates. In other templates ensure to `{% load tetra %}`.

Unlike most Django template tags, the `@` tag can optionally be "open" accepting content, or "closed". To indicate that it is 'closed' it should end with a forward slash `/` such as:

``` django
{% @ MyComponent / %}
```

An open tag is closed with a `{% /@ %}` tag.  This can optionally take the name of the component to aid in following the flow of your template:

``` django
{% @ MyComponent %}
  Some content
{% /@ MyComponent %}
```

!!! note
    Since v0.1.2, Tetra uses PascalCase component references in templates, to match the class name - this is better for finding components and its usages during coding.
    As legacy feature, you can also use the `snake_case_name` to reference your component, but this may be removed in a future version.


## Resolving components

All components belong to a component library, which in turn belong to a "Django App". You can specify a component as either:

  - `ComponentName`

    When you specify only the component name, Tetra attempts to resolve the component **in the current app's `default` library**.

  - `library.ComponentName`

    **Within the current app**, you can specify the component just by the library it is in and its name.

  - `app.ComponentName`

    You can also specify an app name and component. Tetra will look in the `default` library of the app.

  - `app.library.ComponentName`

    With the full component name, you can specify the exact component.

When 2 parts are given (`library.ComponentName` or `app.ComponentName`), resolution is attempted in the order above.


## Dynamically resolved component names

Sometimes you want to determine the component name at runtime, e.g. when the components are part of a plugin system, or when you render components in a for loop. Tetra allows you to determine the component name at runtime. Just use the `=` character before the variable name:

```django
{% for component in components %}
    {% @ =component /%}
{% endfor %}
```

!!! note
    Due to their undetermined nature, Tetra is not able to save dynamic components' states. Hence, **dynamic components are always rendered using their initial state** when loaded in the template. However, their state is saved within the component itself, so if the component reacts to an inside event (e.g. a button click *in* the component), the state is certainly saved and reused.

## Passing Arguments

Both positional and keyword arguments can be passed to a component via the `@` tag. These are passed to the `load` method of the component:

``` python
class MyComponent(Component):
    ...
    def load(self, a_var, something=None, another=False, *args, **kwargs):
        ...
```

``` django
{% @ MyComponent "a string" something=123 another=value_of_a_context_var / %}
```

Your components `load` methods can accept any number of optional positional and keyword arguments by using `*args` and `**kwargs`.

## Passing HTML Attributes

It is common to want to set HTML attributes on the root element of your component - this can be done with the `attrs:` label, followed by a space-separated list of `key=value` pairs, with the "key" being the name of the attribute. The value can be a context variable that will be resolved when rendering.

``` django
{% @ MyComponent attrs: class="my-class" style="font-wight:bold;" / %}
```

These are made available as `attrs` in the component's template, the [attribute  `...` tag](attribute-tag.md) should be used to unpack them into the root tag, its [docs](attribute-tag.md) details how this works.

## Passing Context

By default, outer template context is not passed down to the component's template when rendering; this is to optimise the size of the saved component state. You can explicitly pass context to a component with the `context:` label, followed by a space-separated list of either variable names or `key=value` pairs, where the "key" will be the new name for a context var, and the value either a variable name or a literal.

``` django
{% @ MyComponent context: a_context_var something=old_name another="a string" / %}
```

It is also possible to explicitly pass all template context to a component with the `__all__` argument:

``` django
{% @ MyComponent context: __all__ / %}
```

!!! warning
    This should be used sparingly as the whole template context will be saved with the component's saved (encrypted) state, and sent to the client, see [state security](state-security.md).

In general, if the value is something that is needed for the component to function (and be available to methods or be "public") it should be generally passed as an *argument* [(see above)](#passing-attributes). Passing context is ideal for composing your components with inner content passed down from an outer template [(see passing blocks)](#passing-blocks).

When context is passed using the `_extra_context` class attribute, you can always override these variables in the component tag:

``` django
{{ var }} {# this is "5" #}
{% @ MyComponent context: var=3 / %} {# overrides global var with "3" #}
```

## Passing Blocks

It is possible to pass template `{% block %}`s to a component, overriding or inserting content into the component:

``` django
{% @ MyComponent %}
  {% block title %}
    Some content
  {% endblock %}
{% /@ MyComponent %}
```

> Other frameworks refer to these "blocks" as "slots", but as Tetra is built on Django we use the Django terminology.

You can pass as many blocks to a component as you like:

``` django
{% @ MyComponent %}
  {% block title %}
    A title
  {% endblock %}
  {% block main %}
    Some content
  {% endblock %}
{% /@ MyComponent %}
```

If you pass content to a component without a top-level block it infers that you are targeting the `default` block:

``` django
{% @ MyComponent %}
  Some content
{% /@ MyComponent %}
```

Is the equivalent of:

``` django
{% @ MyComponent %}
  {% block default %}
    Some content
  {% endblock %}
{% /@ MyComponent %}
```

By default, blocks within a component are not available to override in a template that `extends` a template using a component with passed blocks. This is so that you can use components multiple times on a page and not have block names conflict with each other.

It is, however, possible to explicitly expose a block to the wider template so that it can be overridden with the `expose` flag:

``` django
{% @ MyComponent %}
  {% block title expose %}
    Some content
  {% endblock %}
{% /@ MyComponent %}
```

You can also specify under what name a block should be exposed with `expose as [name]`:

``` django
{% @ MyComponent %}
  {% block title expose as header_title %}
    Some content
  {% endblock %}
{% /@ MyComponent %}
```

See [component templates](components.md#templates) for details of how the component handles blocks in its templates.
