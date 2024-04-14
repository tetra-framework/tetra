---
title: Including Tetra CSS and JS
---

# Including Tetra CSS and JS

When processing a `request`, Tetra keeps track of which components have been used on a  page. It then needs to inject the component's CSS and JavaScript into the page. You mark where this is to happen with the `{% tetra_styles %}` and `{% tetra_scripts %}` tags. They should be included in your HTML `<head>`as below.

By default `{% tetra_scripts %}` does not include Alpine.js. You can instruct it to do so by setting `include_alpine=True`. If you would prefer to include Alpine.js yourself you must do so *before* `{% tetra_scripts %}` and also include its [morph plugin](https://alpinejs.dev/plugins/morph).

The `tetra_styles` and `tetra_scripts` need to be loaded via `{% load tetra %}`.

``` django
{% load tetra %}
<html>
  <head>
    ...
    {% tetra_styles %}
    {% tetra_scripts include_alpine=True %}
  </head>
  ...
```