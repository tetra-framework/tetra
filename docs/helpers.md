# Tetra helpers


Tetra offers some helpers that solve common problems.


## Loading indicators / spinners

When clicks are answered with loading times from below 100ms, users perceive this as "instantly". With every +100ms added, the system feels more "laggy". But the most frustrating experience we all know is: clicking on a button that starts a longer loading procedure, and there is no indicator of "busyness" at all, so you don't know if the system is doing something, crashed, or you just did not "click hard enough". So users tend to click again, eventually causing to start the procedure again.

This can be massively improved by "loading indicators", mostly known as "spinners". Tetra offers simple, yet versatile support for loading indicators, with a bit of custom CSS.

Spinners can be placed 

* globally on a page,
* used per component, 
* or even per button that calls a backend method of that component.

### `tx-indicator` attribute

The `tx-indicator` attribute contains a CSS selector that directs Tetra to the element that is used as spinner. During a Tetra request, that element will get the class `tetra-request` automatically.

Here is an example that works with Bootstrap 5 CSS (`.spinner-border`):

```html
<button @click="submit()" tx-indicator="#submit_spinner">Submit</button>
<span id="submit_spinner" class="spinner-border"></span>
```

As you might see, `.spinner-border` is displayed permanently, which is not what we want. So we create some CSS rules that hide spinners per default, and show them only during the request:

```css
.spinner-border {
    display: none;
}
.tetra-request.spinner-border,
.tetra-request .spinner-border {
    display: inline;
}
```

There is nothing that holds you from doing "fancier" transitions than `display: inline`...:

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

It does not matter where you put the spinner, nor how many buttons point to one spinner using `tx-indicator`:

```html
<button @click="increase()" tx-indicator="#spinner">+1</button>
<button @click="decrease()" tx-indicator="#spinner">-1</button>
<span id="spinner" class="spinner-border"></span>
```

You can also include the loading indicators within a button, including full syntactic ARIA sugar:

```html
<button class="btn btn-primary" type="button" @click="$el.disabled=true; foo()" tx-indicator="#spinner">
  <span id="spinner" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
  Loading...
</button>
```

This is all you need. Of course, you can implement this pattern in any other framework, be it Bulma, Tailwind or others.


Credits: The indicator functionality is closely modeled after the [hx-indicator](https://htmx.org/attributes/hx-indicator/) feature of HTMX.
