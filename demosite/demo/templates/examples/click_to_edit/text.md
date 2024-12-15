---
title: Click to Edit
---

# Click to Edit

The *click-to-edit* pattern enables inline editing of a record without refreshing the page.

This is a simple way to implement this as Tetra component, including save/cancel buttons:
{% md_include_source "demo/components/examples/click_to_edit/__init__.py" %}
{% md_include_source "demo/components/examples/click_to_edit/click_to_edit.html" %}


If you click the text, it is replaced with an input form field.

You could also imagine to do that in other ways:

* by hiding the borders of the input field in display mode, and showing them again using Alpine when in edit_mode.
* without buttons, just by using the `@blur` event for saving.