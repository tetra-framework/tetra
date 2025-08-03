---
title: Helper filters & tags
---

# `if` and `else` Template Filters

The `if` and `else` template filters are provided to enable conditional attribute values with the [`...` attribute template tag](attribute-tag.md) within a component's template, where they are automatically available:

``` django
<div {% ... class="class1"|if:variable_name|else:"class2" %}>
   component content
</div>
```

If you want to use `if` and `else` in other Django templates, be sure to `{% load tetra %}`.

## `if` Filter

When the value of the right hand argument evaluates to `True` it returns the value of its left hand argument. When the value of the right hand argument evaluates to `False` it returns an empty string `""` (a falsy value).

So when setting a class:

``` django
<div {% ... class="class1"|if:my_var %}>
```

if `my_var=True` you will generate this HTML:

``` html
<div class="class1">
```

if it's `False` then you will receive this:

``` html
<div class="">
```

## `else` Filter

When the value of the left hand argument evaluates to `True` it returns the value of its left hand argument. When the value of the left hand argument evaluates to `False` (such as an empty string `""`) it returns the value of its right hand argument.

So with this:

``` django
<div {% ... data-something=context_var|else:"Default Value" %}>
```

If `context_var="Some 'Truthy' String"` then you will generate this HTML:

``` html
<div data-something="Some 'Truthy' String">
```

if it's `False` then you will receive this:

``` html
<div data-something="Default Value">
```

## Chaining

`if` and `else` can be chained together, so with this:

``` django
<div {% ... class="class1"|if:variable_name|else:"class2" %}>
```

If `variable_name="A 'Truthy' Value"` then you will generate this HTML:

``` html
<div class="class1">
```

if it's `False` then you will receive this:

``` html
<div class="class2">
```

It is possible to further chain the filters such as:

``` django
<div {% ... class="class1"|if:variable1|else:"class2"|if:variable2|else:"class3" %}>
```

## The `livevar` tag

When variables are displayed in components, a common pattern is that a string should reflect a variable name "live", as you type. While a normal Django variable `{{ title }}` will get only updated after the next rendering of the component (e.g. after you call a backend method), Tetra provides a convenience way to render a variable instantly in the frontend using Alpine.js: `{% livevar title %}`.

```django
<div class="card">
  <div class="card-title">Current title: {{ title }} - New title: {% livevar title %}</div>
  <div class="card-body">
    <input type="text" x-model="title">
  </div>
  <div class="card-footer">The title is: {% livevar "title" %}</div> {# with quotes is also possible#}
</div>
```
It does not matter if you put the variable into quotes or not.
Technically, it simply renders a `<span x-text="title"></span>` and let Alpine.js update the inner HTML content with the variable dynamically. Per default, *livevar* uses a plain `span` HTML tag, you can change that using the `tag` parameter: 

```django
{% livevar first_name tag="div" %}
``` 