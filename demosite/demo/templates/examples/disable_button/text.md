---
title: Disable submit button
---

# Disable submit button

When submitting a form, many users tend to double-click the `submit` button, leading to double entries in the databases, if the timing was right ;-)

It is an easy pattern to just disabling the button right after clicking it. You can do two things in the `@click` listener: disable the button *and* call `submit()`.

{% md_include_source "demo/components/examples/disable_button/disable_button.html" %}


If you click the button, it is disabled, without altering the state. When the component is reloaded, the buttin is enabled again (for a create form), but mostly, you will redirect to another page using `self.client._redirect(...)` 

