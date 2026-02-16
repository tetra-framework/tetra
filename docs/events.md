# Tetra client side JavaScript events

There are some events that occur during the tetra component life cycle. You can use them to hook into.


On the client, there are certain javascript events fired when certain things happen. You can react on that using Alpine's `x-on` or by using custom Javascript code.

If not stated otherwise, all events have the actual component as `component` payload attached in `event.detail`.

## Event list

### `tetra:before-request`

This event is triggered before a component method is called. It can be used to implement loading indicators or prepare the UI for a pending server action.

### `tetra:after-request`

This event fires after a component method request has completed — whether the request was successful or if a network error occurred. It can be used alongside `tetra:before-request` to hide loading indicators.

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

### `tetra:component-stale`

This event is fired when a component's state becomes stale, typically because database objects it references have been deleted by another client. When this happens, the component is automatically removed from the DOM after this event fires.

This event allows you to perform custom cleanup or notify users before the component is removed.

#### Details
* `component`: the component instance with stale state
* `error`: an object containing `code: "StaleComponentState"` and a user-friendly `message`

**Example:**
```html
<div @tetra:component-stale="alert('A component was removed because its data no longer exists')">
  <!-- Your component -->
</div>
```

**Note:** This is a global event dispatched on `document`, so use `.document` modifier to listen for it from any component.

### `tetra:new-message`

After a request returns a response, Tetra fires this event if there are new messages from the Django messaging system. You can react to these messages, e.g. display them in a component.

#### Details
* `messages`: a list of message objects, see [messages](messages.md)


## Component subscription 

These events are fired after a websocket subscription returned, successfully or unsuccessfully.

#### Details:
* `component`: this,
* `group`: the group name of the subscription
* `message`: (Optional) message in case of an error.

### `tetra:component-subscribed`

When a component subscription was completed successfully.

### `tetra:component-resubscribed`

When a component subscription was re-issued. Rarely used.

### `tetra:component-unsubscribed`

When a component subscription was redacted.

### `tetra:component-subscription-error`

When a component subscription/unsubsription process did not succeed.

### `tetra:websocket-connected`

Triggered when the WebSocket connection is successfully established or re-established. This indicates that reactive features are now available.

### `tetra:websocket-disconnected`

Triggered when the client's online status changes to `offline`. This happens either when a WebSocket connection is closed or when a ping request to the server times out. See [Online/Offline Status](online-status.md) for details.

## Offline Queue Events

These events are dispatched during offline queue operations. See [Offline Queue](offline-queue.md) for detailed documentation.

### `tetra:call-queued`

Fired when a component method call is queued because the connection is offline.

#### Details
* `component`: The component instance
* `methodName`: Name of the queued method
* `queueLength`: Current number of items in the queue

### `tetra:queue-processing-start`

Fired when the offline queue begins processing after the connection is restored. This is a global event dispatched on `document`.

#### Details
* `queueLength`: Number of calls being processed

### `tetra:queue-processing-complete`

Fired when the offline queue finishes processing. This is a global event dispatched on `document`.

#### Details
* `processedCount`: Number of calls processed in this batch
* `remainingCount`: Number of calls still queued (failed with 500+ errors)

### `tetra:call-reconciled`

Fired when a queued call is successfully reconciled with the server after being offline.

#### Details
* `component`: The component instance
* `methodName`: Name of the reconciled method
* `result`: Result returned from the server

### `tetra:call-rolled-back`

Fired when a queued call is rolled back due to authentication/authorization errors (401/403).

#### Details
* `component`: The component instance
* `methodName`: Name of the rolled back method
* `status`: HTTP status code (401 or 403)
* `reason`: Reason for rollback (e.g., 'auth_error')

### `tetra:call-conflict`

Fired when a queued call results in a 409 Conflict response, indicating stale component state. The component will be automatically refreshed from the server.

#### Details
* `component`: The component instance
* `methodName`: Name of the conflicted method

### `tetra:call-failed`

Fired when a queued call fails permanently (4xx errors other than 401/403/409).

#### Details
* `component`: The component instance
* `methodName`: Name of the failed method
* `status`: HTTP status code

### `tetra:state-rolled-back`

Fired after component state is restored to a previous snapshot due to an error during queue processing.

#### Details
* `component`: The component instance

### `tetra:call-replayed-without-component`

Fired when a queued call is successfully replayed using snapshot state without finding the component in the DOM. This is a global event dispatched on `document`.

#### Details
* `componentId`: The component ID that was not found
* `methodName`: Name of the replayed method
* `response`: Server response data
