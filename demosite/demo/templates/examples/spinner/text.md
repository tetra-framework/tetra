---
title: Loading indicator / spinner
---

# Loading indicator / spinner

A common pattern is showing loading indicators (also called "spinner"), whenever a request duration is longer than the usual user is inclined to wait, without getting nervous...

There are several spinners available in frameworks like [Bootstrap](https://getbootstrap.com/docs/5/components/spinners/) or [tabler.io](https://docs.tabler.io/ui/components/spinners) (which builds upon BS5). Even Tailwind uses an [animation class](https://tailwindcss.com/docs/animation#adding-a-spin-animation) to produce spinners.

Tetra tries to be as framework-agnostic as possible, here we'll use Boostrap 5 in the example:

{% md_include_source "demo/components/examples/spinner/__init__.py" %}
{% md_include_source "demo/components/examples/spinner/spinner.html" %}

The spinner is hidden by default and shown when a tetra request is in flight.

You can also achieve the hiding with `opacity: 0` and `opacity:1` with a `transition` to make it smoother, see the [spinner documentation](https://tetra.readthedocs.io/en/stable/helpers/#loading-indicators-spinners) for details.

You can click the buttons below, the spinners are shown for the period of the tetra request and hidden again afterwords, regardless of where the spinner is located in the page.


External spinner on the page (outside the component): <span id="spinner-external" class="spinner-border spinner-border-sm"></span>
