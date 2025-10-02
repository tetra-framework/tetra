# Tetra client side JavaScript events

There are some events that occur during the tetra component life cycle. You can use them to hook into.


On the client, there are certain javascript events fired when certain things happen. You can react on that using Alpine's `x-on` or by using custom Javascript code.

If not stated otherwise, all events have the actual component as `component` payload attached in `event.detail`.

## Event list

### `tetra:before-request`

This event fires after a component method has completed — whether the request was successful (even if the response includes an HTTP error like 404) or if a network error occurred. It can be used alongside `tetra:before-request` to implement custom behavior around the full request lifecycle, such as showing or hiding a loading indicator.


### `tetra:after-request`

This event is triggered before a component method is called.

### `tetra:child-component-init`

Whenever a child component is initialized, this event is fired. This is mainly used internally within Tetra.

### `tetra:child-component-destroy`

Called before a child component is going to be destroyed. This is mainly used internally within Tetra.

### `tetra:component-updated`
This event is fired after a component has called a public method and the new HTML is completely morphed into the DOM.
It is also fired after a component has been replaced.

```html
<div @tetra:component-updated="message='component was updated'">
  <span x-text="message">Original text</span>
</div>
```

### `tetra:component-data-updated`

The same goes for data updates: the event is fired after a data update without HTML changes was finished.

### `tetra:component-before-remove`

Right before a component is removed using `self.client._removeComponent()` this event is triggered.

### `tetra:new-message`

After a request returns a response, Tetra fires this event if there are new messages from the Django messaging system. You can react to these messages, e.g. display them in a component.

#### Details
* `messages`: a list of message objects, see [messages](messages.md)

### `tetra:component-subscribed`

After a successful subscription to a group, the component fires this event.

#### Details
* `group`: the group the component was subscribed to.


## Component subscription 

These events are fired after a websocket subscription returned, successfully or unsuccessfully.

#### Details:
* `component`: this,
* `group`: the group name of the subscription
* `message`: (Optional) message in case of an error.

### `tetra:component-subscribed`

When a component subscription was completed successfully.

### `tetra:component-unsubscribed`

When a component subscription was redacted.

### `tetra:component-subscription-error`

When a component subscription/unsubsription process did not succeed.
 