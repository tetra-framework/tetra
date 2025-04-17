---
title: Click to Edit
---

# Loading indicator / spinner

A common pattern is showing loading indicator (also called "spinner"), whenever a request duration is longer than the usual user is inclined to wait, without getting nervous...


{% md_include_source "demo/components/examples/spinner/__init__.py" %}
{% md_include_source "demo/components/examples/spinner/spinner.html" %}

You'll need a bit of CSS to get this to work, as you have to hide the spinner per default:

{% md_include_source "demo/components/examples/spinner/spinner.css" %}

You can also accomplish the hiding with `opacity: 0` and `opacity:1` with a `transition` to make it smoother.

You can click the button below, the spinner is shown for the period of the tetra request and hidden again afterwords.