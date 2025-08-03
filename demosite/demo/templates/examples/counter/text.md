---
title: Counter
---

# Counter demo

The "counter" is basically the "Hello World" demo of components. It is a simple demo of how to use Tetra components.

The component itself only provides a `count` attribute, and a public `increment()` method.

 'nuff said, show me the code.

{% md_include_component_source "examples.Counter" %}

Rendering is straightforward.

{% md_include_component_template "examples.Counter" %}

Note below in the demo how fast Tetra rendering is. Component updates almost feel as fast as native Javascript.
