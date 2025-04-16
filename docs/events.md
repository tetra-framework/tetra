# Tetra events

There are some events that occur during the tetra component life cycle. You can use them to hook into.


On the client, there are certain javascript events fired when certain things happen. You can react on that using Alpine's `x-on` or by using custom Javascript code.

All events have the actual component as `component` payload attached in `event.detail`.

## Event list

### `tetra:afterRequest`

This event fires after a component method has completed — whether the request was successful (even if the response includes an HTTP error like 404) or if a network error occurred. It can be used alongside `tetra:beforeRequest` to implement custom behavior around the full request lifecycle, such as showing or hiding a loading indicator.


### `tetra:beforeRequest`

This event is triggered before a component method is called.


### `tetra:componentUpdated`
This event is fired after a component has called a public method and the new HTML is completely morphed into the DOM.
It is also fired after a component has been replaced.

```html
<div @tetra:componentUpdated="message='component was updated'">
  <span x-text="message">Original text</span>
</div>
```

### `tetra:componentDataUpdated`

Same goes for data updates - the event is fired after a data update without HTML changes was finished.

### `tetra:componentBeforeRemove`

Right before a component is removed using `self.client._removeComponent()` this event is triggered.

### `tetra:childComponentDestroy`

Called before a child component is going to be destroyed.

#### Details

* `component` - The component that is destroyed