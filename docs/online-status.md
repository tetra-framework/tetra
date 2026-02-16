---
title: Offline Mode
---
# Online/offline Status

Tetra includes a built-in system to track the "online" status of the client. This is particularly useful for reactive components that rely on a stable WebSocket connection.

## The `tetraStatus` Store

Tetra automatically initializes an Alpine.js global store named `tetraStatus` (unless it's already defined). You can use this store in your templates to react to connection changes.

### Properties

*   `$store.tetraStatus.online`: A boolean indicating if the client is currently considered "online".
*   `$store.tetraStatus.lastActivity`: A timestamp (in milliseconds) of the last successful communication with the server (WebSocket message received or HTTP request completed).

### Example Usage

You can use Alpine's `x-show` or `:class` to display connection status to your users:

```html
<!-- Display a badge when offline -->
<div 
    x-show="!$store.tetraStatus?.online" 
    class="alert alert-warning" 
    x-cloak
>
    You are currently offline. Some features may be unavailable.
</div>

<!-- Change status indicator color -->
<div :class="$store.tetraStatus?.online ? 'text-success' : 'text-danger'">
    ● <span x-text="$store.tetraStatus?.online ? 'Connected' : 'Disconnected'"></span>
</div>
```
Make sure you only use Alpine store variables within a `Component` and not elsewhere at the page, as it needs to have 
the Alpine store initialized and accessible.

## How it Works

The online status is maintained through several mechanisms:

1.  **Activity Tracking**: Every successful HTTP request made via a Tetra component and every received WebSocket message resets the activity timer and sets the status to `online`.
2.  **WebSocket Connection**: If the WebSocket connection is explicitly closed, the status is immediately set to `offline`.
3.  **Ping/Pong Mechanism**: If no activity is detected for a configurable period (default: 10 seconds), Tetra sends a `ping` message to the server via WebSocket. If no `pong` is received within a timeout (default: 5 seconds), the status is set to `offline`.

## Configuration

TODO

## Events

When the client goes offline, a custom event is dispatched on the `document`:

### `tetra:websocket-disconnected`

Triggered when the status changes to `offline`. This happens either when a WebSocket connection is closed or when a ping request times out.

```javascript
document.addEventListener('tetra:websocket-disconnected', () => {
    console.log("Oh no! We lost connection to the server!");
});
```
