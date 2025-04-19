# Tetra helpers


Tetra offers some helpers that solve common problems.


## Loading indicators / spinners

When clicks are answered with loading times from below 100ms, users perceive this as "instantly". With every +100ms added, the system feels more "laggy". But the most frustrating experience we all know is: clicking on a button that starts a longer loading procedure, and there is no indicator of "busyness" at all, so you don't know if the system is doing something, crashed, or you just did not "click hard enough". So users tend to click again, eventually causing to start the procedure again.

This can be massively improved by "loading indicators", mostly known as "spinners". Tetra offers simple, yet versatile support for loading indicators, with a bit of custom CSS.

Spinners can be placed 

* globally on a page,
* used per component, 
* or even per button that calls a backend method of that component.

### The `tetra-request` class

While a request is in flight, the element that initiated the request (e.g. a button) receives the `tetra_request` class automatically. You can use that to show busy indicators within the button, just by adding some css.

Here is an example that works with Bootstrap 5 CSS (`.spinner-border`):

```css
.spinner-border {
    display: none;
}
.tetra-request.spinner-border,
.tetra-request .spinner-border {
    display: inline-block;
}
```
Now place a "spinner" into your button:

```html
<button class="btn" @click="submit()">
  Submit
  <span class="spinner-border"></span>
</button>
```

This is all you need to get a simple loading indicator working, for within an element.

### `tx-indicator` attribute

If you don't want to place the indicator **into** the calling element, you have to tell Tetra somehow where this indicator is:

The `tx-indicator` attribute contains a CSS selector that directs Tetra to the element that is used as loading indicator. During a Tetra request, **that element** will get the class `tetra-request` now.

`tx-indicator` elements will take precedence over any inline spinners defined directly in the element. This means if both an inline spinner and a tx-indicator target are specified, the tx-indicator target will be used and the inline spinner will be ignored.

```html
<button @click="submit()" tx-indicator="#submit_spinner">Submit</button>
<span id="submit_spinner" class="spinner-border"></span>
```

There is nothing that holds you from doing "fancier" transitions than `display: inline`:

```css
.spinner-border {
    opacity: 0;
    transition: opacity 500ms ease-in;
}
.tetra-request .spinner-border, 
.tetra-request.spinner-border {
    opacity: 1;
}
```

It does not matter where you put the spinner, nor how many elements point to one spinner using `tx-indicator`:

```html
<button @click="increase()" tx-indicator="#spinner">+1</button>
<button @click="decrease()" tx-indicator="#spinner">-1</button>
<button @click="foo()" tx-indicator="#spinner">foO!</button>
...
<span id="spinner" class="spinner-border"></span>
```

You can also add full syntactic ARIA sugar:

```html
<button class="btn btn-primary" type="button" @click="$el.disabled=true; foo()" tx-indicator="#spinner">
  <span id="spinner" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
  Loading...
</button>
```

This is all you need. Of course, you can implement this pattern in any other framework than Bootstrap, be it Bulma, Tailwind or others.


Credits: The indicator functionality is closely modeled after the [hx-indicator](https://htmx.org/attributes/hx-indicator/) feature of HTMX.
