---
title: The `@` Component Tag
---

# `@` Component Tag

Tetra components are included in a template with the `{% @ [component name] %}` template tag.

The component tag is automatically available in your components' templates. In other templates ensure to `{% load tetra %}`.

Unlike most Django template tags, the `@` tag can optionally be "open" accepting content, or "closed". To indicate that it is 'closed' it should end with a forward slash `/` such as:

``` django
{% @ my_component / %}
```

An open tag is closed with a `{% /@ %}` tag.  This can optionally take the name of the component to aid in following the flow of your template:

``` django
{% @ my_component %}
  Some content
{% /@ my_component %}
```

## Resolving components

All components belong to a component library, which in turn belong to a "Django App". You can specify a component as either:

  - `component_name`

    When you only specify the component name, Tetra attempts to resolve the component in the current app's `default` library.

  - `library.component_name`

    You can specify which library the component is in within the current app.

  - `app.component_name`

    You can also specify an app name and component. Tetra will look in the `default` library of the app.

  - `app.library.component_name`

    Finally, you can fully specify the component path.

Resolution is attempted in the order above.

## Passing Arguments

Both positional and keyword arguments can be passed to a component via the `@` tag. These are passed to the `load` method of the component:

``` python
class MyComponent(Component):
    ...
    def load(self, a_var, something=None, another=False):
        ...
```

``` django
{% @ my_component "a string" something=123 another=value_of_a_context_var / %}
```

Your components `load` methods can accept any number of optional positional and keyword arguments by using `*args` and `**kwargs`.

## Passing Attributes

It is common to want to set HTML attributes on the root element of your component  - this can be done with the `attrs:` label, followed by a space-separated list of `key=value` pairs, with the "key" being the name of the attribute. The value can be a context variable that will be resolved when rendering.

``` django
{% @ my_component attrs: class="my-class" style="font-wight:bold;" / %}
```

These are made available as `attrs` in the component's template, the [attribute  `...` tag](attribute-tag.md) should be used to unpack them into the root tag, its [docs](attribute-tag.md) details how this works.

## Passing Context

By default, outer template context is not passed down to the component's template when rendering; this is to optimise the size of the saved component state. You can explicitly pass context to a component with the `context:` label, followed by a space-separated list of either variable names or `key=value` pairs, where the "key" will be the new name for a context var, and the value either a variable name or a literal.

``` django
{% @ my_component context: a_context_var something=old_name another="a string" / %}
```

It is  also possible to explicitly pass all template context to a component with the `**context` argument:

``` django
{% @ my_component context: **context / %}
```

This should be used sparingly as the whole template context will be saved with the component's saved (encrypted) state, and sent to the client, see [state security](state-security.md).

In general, if the value is something that is needed for the component to function (and be available to methods or be "public") it should be passed as an *argument* [(see above)](#passing-attributes.md). Passing context is ideal for composing your components with inner content passed down from an outer template [(see passing blocks)](#passing-blocks).

## Passing Blocks

It is possible to pass template `{% block %}`s to a component, overriding or inserting content into the component:

``` django
{% @ my_component %}
  {% block title %}
    Some content
  {% endblock %}
{% /@ my_component %}
```

> Other frameworks refer to these "blocks" as "slots", but as Tetra is built on Django we use the Django terminology.

You can pass as many blocks to a component as you like:

``` django
{% @ my_component %}
  {% block title %}
    A title
  {% endblock %}
  {% block main %}
    Some content
  {% endblock %}
{% /@ my_component %}
```

If you pass content to a component without a top-level block it infers that you are targeting the `default` block:

``` django
{% @ my_component %}
  Some content
{% /@ my_component %}
```

Is the equivalent of:

``` django
{% @ my_component %}
  {% block default %}
    Some content
  {% endblock %}
{% /@ my_component %}
```

By default, blocks within a component are not available to override in a template that `extends` a template using a component with passed blocks. This is so that you can use components multiple times on a page and not have block names conflict with each other.

It is, however, possible to explicitly expose a block to the wider template so that it can be overridden with the `expose` flag:

``` django
{% @ my_component %}
  {% block title expose %}
    Some content
  {% endblock %}
{% /@ my_component %}
```

You can also specify under what name a block should be exposed with `expose as [name]`:

``` django
{% @ my_component %}
  {% block title expose as header_title %}
    Some content
  {% endblock %}
{% /@ my_component %}
```

See [component templates](components.md#templates) for details of how the component handles blocks in its templates.
