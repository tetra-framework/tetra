# Tetra helpers

Tetra offers some helpers that solve common problems.


## Loading indicators / spinners

When clicks are answered with loading times from below 100ms, users perceive this as "instantly". With every +100ms added, the system feels more "laggy". But the most frustrating experience we all know is: clicking on a button that starts a longer loading procedure, and there is no indicator of "busyness" at all, so you don't know if the system is doing something, has crashed, or you just did not "click hard enough". So users tend to click again, eventually causing your app to start the procedure again.

This can be massively improved by adding "loading indicators", mostly known as "spinners". Tetra offers simple, yet versatile support for loading indicators, with a bit of custom CSS.

Spinners can be placed 

* globally on a page (and reused by multiple components),
* anywhere within a component, 
* or even into one element of your component, e.g., a button.

But first things first:

### The `tetra-request` class

While a request is in flight, *the element that initiated the request* (e.g. a button, **not** the component!) receives a `tetra-request` class automatically. You can use that to show busy indicators within the button, by adding custom CSS rules.


### The `t-indicator` attribute and `tetra-indicator` class

Tetra provides built-in CSS rules for loading indicators without requiring custom CSS.

When you add a `t-indicator` attribute to an element that initiates a request, Tetra finds the element matching that CSS selector and applies the `tetra-indicator-{component_id}` class, binding the indicator to your component. Multiple components can share the same indicator element (e.g., a global spinner), with each receiving a separate binding.

Without a `t-indicator` attribute, Tetra automatically shows/hides elements with the `tetra-indicator` class **inside** the requesting element.


```html
<button @click="submit()" t-indicator="#submit_spinner">
  Submit
  <!-- the spinner is shown here (through 'tetra-indicator') -->
  <span class="tetra-indicator spinner-border spinner-border-sm ms-2"></span>
</button>

<!-- or -->
<button @click="submit()" t-indicator="#submit_spinner">Submit</button>

<!-- ...and somewhere else on the page: -->
<span id="submit_spinner" class="spinner-border"></span>
```


### Custom CSS

However, there is nothing that holds you from doing "fancier" transitions than `display: none`:

```css
.spinner-border {
    opacity: 0;
    transition: opacity 500ms ease-in;
}
.tetra-request + .spinner-border, 
.tetra-request .spinner-border {
    opacity: 1;
}
```

It does not matter where you put the spinner, nor how many elements point to one spinner using `t-indicator`:

```html
<button @click="increase()" t-indicator="#spinner">+1</button>
<button @click="decrease()" t-indicator="#spinner">-1</button>
<button @click="foo()" t-indicator="#spinner">foO!</button>
...
<span id="spinner" class="spinner-border"></span>
```

You can also add syntactic ARIA sugar:

```html
<button class="btn btn-primary" type="button" @click="$el.disabled=true; foo()" t-indicator="#spinner">
  <span id="spinner" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
</button>
```

This is all you need. Of course, you can implement this pattern in any other framework than Bootstrap, be it Bulma, Tailwind, or others.


Credits: The indicator functionality is loosely modeled after the [hx-indicator](https://htmx.org/attributes/hx-indicator/) feature of HTMX.
