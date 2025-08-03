---
title: "The `...` Attribute"
---

# `...` Attribute Tag

HTML attributes regularly need to be set programmatically in a template. To aid in this, Tetra has the "attribute tag", available as `...` (three periods) as it "unpacks" the arguments provided to it as HTML attributes.

The attributes tag is automaticity available in your **component templates**. In other templates be sure to `{% load tetra %}`.

``` django
{% load tetra %}
<div {% ... a_dict_of_attributes class="test" class=list_of_classes 
  checked=a_boolian_varible %}>
```

All Tetra components have an `attrs` context available, which is a `dict` of attributes that have been passed to the component when it is included in a template with the [`@` tag](component-tag.md). It can be unpacked as HTML attributes on your root node:

``` django
<div {% ... attrs %}>
```

The attribute tag can take the following arguments:

- A (not keyword) variable resolving to a `dict` of attribute names mapped to values. This is what the `attrs` context variable is.

- An attribute name and literal value such as `class="test"`.

- An attribute name and context variable such as `class=list_of_classes`.

The attributes are processed left to right, and if there is a duplicate attribute name the last occurrence is used (there is a special case for [`class`](#class-attribute) and [`style`](#style-attribute)). This allows you to provide both default values and overrides. In the example below the `id` has a default value of `"test"` but can be overridden when the component is used via the `attrs` variable. It also forces the `title` attribute to a specific value overriding any set in `attrs`.

``` django
<div {% ... id="test" attrs title="Forced Title" %}>
```

## Boolean attributes

Boolean values have a special case. If an attribute is set to `False` it is not included in the final HTML. If an attribute is set to `True` it is included in the HTML as just the attribute name, such as `<input checked>`.

## Class attribute

The `class` attribute treats each class name as an individual option concatenating all passed classes. In the example below all classes will appear on the final element:

``` django
{# where the component is used #}
{% MyComponent attrs: class="class1" / %}

{# component template with a_list_of_classes=["classA", "classB"] #}
<div {% ... class="class2" attrs class="class3 class4" class=a_list_of_classes %}>
```

Resulting html:

``` html
<div class="class2 class1 class3 class4 classA classB">
```

## Style attribute

There is a special case for the `style` attribute, similar to the `class` attribute. All passed styes are split into individual property names with the final value for property name used in the final attribute.

``` django
<div {% ... style="color:red; font-size:2em;" style="color:blue;" %}>
```

Would result in:

``` html
<div style="font-size:2em; color:blue;">
```

!!! note
    Tetra currently does not understand that a style property can be applied in multiple ways. Therefore, if you pass both `margin-top: 1em` and `margin: 2em 0 0 0`, both will appear in the final HTML style tag, with the final property taking precedence in the browser.

## Conditional values

The [`if` and `else` template filters](if-else-filters.md) are provided to enable conditional attribute values:

``` html
<div {% ... class="class1"|if:variable_name|else:"class2" %}>
```

See the documentation for the [`if` and `else` template filters](if-else-filters.md).
