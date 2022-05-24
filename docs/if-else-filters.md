Title: if and else Template Filters

# `if` and `else` Template Filters

The `if` and `else` template filters are provided to enable conditional attribute values with the [`...` attribute template tag](attribute-tag):

``` django
<div {% ... class="class1"|if:variable_name|else:"class2" %}>
```

The `if` and `else` template filters are automatically available in your components' templates, in other templates be sure to `{% load tetra %}`.

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

It is possible to further chain the the filters such as:

``` django
<div {% ... class="class1"|if:variable1|else:"class2"|if:variable2|else:"class3" %}>
```