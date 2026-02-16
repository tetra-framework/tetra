---
title: Offline Queue
---

# Offline Queue & Optimistic UI

Tetra includes a robust offline queue system that allows your application to continue functioning even when the network connection is temporarily unavailable. This system provides optimistic UI updates, automatic queueing of failed requests, and intelligent reconciliation when the connection is restored.

## Overview

The offline queue system implements the **Optimistic UI + Offline Queue + Reconciliation** pattern:

1. **Optimistic UI**: Updates happen immediately in the browser for responsive UX
2. **Offline Queue**: Method calls are queued when offline and replayed when online
3. **Reconciliation**: Server responses are handled with appropriate rollback strategies

## How It Works

### Automatic Queueing

When a component method is called and the connection is unavailable, Tetra automatically:

1. **Captures a snapshot** of the component's current state (including encrypted state)
2. **Queues the method call** with all necessary context for replay
3. **Returns immediately** without blocking the UI
4. **Dispatches events** to notify your application

The queue is automatically processed when:

- The WebSocket connection is restored
- The browser's online status changes (detected via `navigator.onLine`)
- A successful HTTP request completes (triggering retry of queued calls)

### Component State Snapshots

Before each method call, Tetra captures a complete snapshot of the component including:

- All public properties (reactive state)
- Encrypted server-side state (`__state`)
- Component HTML (for rollback)
- Component ID and key (for correct identification)

This snapshot enables:

- **Accurate replay** even if the component has been removed from DOM
- **Reliable rollback** if the server rejects the request
- **Correct component identification** even when component IDs are reused

### Reconciliation Strategies

When processing queued calls, Tetra handles different HTTP status codes with appropriate strategies:

| Status Code | Strategy | Description |
|-------------|----------|-------------|
| **200 (Success)** | Apply response | Server accepted the request, apply the response normally |
| **401/403 (Auth)** | Rollback, don't retry | Authentication/authorization failed, restore previous state |
| **409 (Conflict)** | Refresh component | State conflict detected, fetch fresh state from server |
| **500+ (Server Error)** | Rollback and retry | Temporary server issue, restore state and retry later |
| **Network Error** | Rollback and retry | Connection issue, restore state and retry when online |

### Component Identification

Tetra uses a dual-lookup system to find the correct component during replay:

1. **Primary lookup**: Find by `component_id`
2. **Validation**: Verify the component `key` matches
3. **Fallback**: If key mismatch, search all components by `key`
4. **Snapshot replay**: If component not found, replay using snapshot state

This ensures the correct component is updated even when:

- Component IDs are reused (common in loops)
- Components are deleted (optimistic delete)
- Components are moved or reordered

## Events

The offline queue system dispatches several events you can listen to:

### Queue Management Events

#### `tetra:call-queued`
Fired when a method call is added to the offline queue.

```javascript
document.addEventListener('tetra:call-queued', (event) => {
    console.log(`Queued: ${event.detail.methodName}`);
    console.log(`Queue length: ${event.detail.queueLength}`);
});
```

**Event detail properties:**
- `component`: The component instance
- `methodName`: Name of the queued method
- `queueLength`: Current number of items in queue

#### `tetra:queue-processing-start`
Fired when the queue begins processing after coming back online.

```javascript
document.addEventListener('tetra:queue-processing-start', (event) => {
    console.log(`Processing ${event.detail.queueLength} queued calls`);
});
```

**Event detail properties:**
- `queueLength`: Number of calls being processed

#### `tetra:queue-processing-complete`
Fired when queue processing completes.

```javascript
document.addEventListener('tetra:queue-processing-complete', (event) => {
    console.log(`Processed: ${event.detail.processedCount}`);
    console.log(`Remaining: ${event.detail.remainingCount}`);
});
```

**Event detail properties:**
- `processedCount`: Number of calls processed in this batch
- `remainingCount`: Number of calls still queued (failed with 500+ errors)

### Reconciliation Events

#### `tetra:call-reconciled`
Fired when a queued call is successfully reconciled with the server.

```javascript
component.$el.addEventListener('tetra:call-reconciled', (event) => {
    console.log(`Reconciled: ${event.detail.methodName}`);
});
```

**Event detail properties:**
- `component`: The component instance
- `methodName`: Name of the reconciled method
- `result`: Result returned from the server

#### `tetra:call-rolled-back`
Fired when a queued call is rolled back due to auth errors (401/403).

```javascript
component.$el.addEventListener('tetra:call-rolled-back', (event) => {
    console.log(`Rolled back: ${event.detail.methodName}`);
    console.log(`Status: ${event.detail.status}`);
    console.log(`Reason: ${event.detail.reason}`);
});
```

**Event detail properties:**
- `component`: The component instance
- `methodName`: Name of the rolled back method
- `status`: HTTP status code (401 or 403)
- `reason`: Reason for rollback (e.g., 'auth_error')

#### `tetra:call-conflict`
Fired when a queued call results in a 409 Conflict (stale state).

```javascript
component.$el.addEventListener('tetra:call-conflict', (event) => {
    console.log(`Conflict detected for: ${event.detail.methodName}`);
    // Component will be automatically refreshed from server
});
```

**Event detail properties:**
- `component`: The component instance
- `methodName`: Name of the conflicted method

#### `tetra:call-failed`
Fired when a queued call fails permanently (4xx errors other than 401/403/409).

```javascript
component.$el.addEventListener('tetra:call-failed', (event) => {
    console.log(`Failed: ${event.detail.methodName}`);
    console.log(`Status: ${event.detail.status}`);
});
```

**Event detail properties:**
- `component`: The component instance
- `methodName`: Name of the failed method
- `status`: HTTP status code

#### `tetra:state-rolled-back`
Fired after component state is restored to a previous snapshot.

```javascript
component.$el.addEventListener('tetra:state-rolled-back', (event) => {
    console.log('State restored to pre-call snapshot');
});
```

**Event detail properties:**
- `component`: The component instance

#### `tetra:call-replayed-without-component`
Fired when a call is successfully replayed using snapshot state without finding the component in DOM.

```javascript
document.addEventListener('tetra:call-replayed-without-component', (event) => {
    console.log(`Replayed ${event.detail.methodName} for deleted component`);
});
```

**Event detail properties:**
- `componentId`: The component ID that was not found
- `methodName`: Name of the replayed method
- `response`: Server response data

## Example: UI Feedback for Offline Operations

You can use these events to provide rich feedback to users:

```html
<div x-data="{
    queueLength: 0,
    processingQueue: false,
    showOfflineNotice: false
}">
    <!-- Offline notice -->
    <div
        x-show="showOfflineNotice && queueLength > 0"
        class="alert alert-info"
        x-cloak
    >
        <span x-show="!processingQueue">
            <strong>Offline:</strong>
            <span x-text="queueLength"></span> action(s) queued
        </span>
        <span x-show="processingQueue">
            Syncing queued actions...
        </span>
    </div>

    <!-- Your component content -->
</div>

<script>
document.addEventListener('tetra:call-queued', (event) => {
    Alpine.store('offlineStatus', {
        queueLength: event.detail.queueLength,
        showOfflineNotice: true
    });
});

document.addEventListener('tetra:queue-processing-start', () => {
    Alpine.store('offlineStatus', {
        processingQueue: true
    });
});

document.addEventListener('tetra:queue-processing-complete', (event) => {
    Alpine.store('offlineStatus', {
        processingQueue: false,
        queueLength: event.detail.remainingCount,
        showOfflineNotice: event.detail.remainingCount > 0
    });
});
</script>
```

## Example: Handling Conflicts

```html
<div x-data="{ showConflictWarning: false }">
    <div
        x-show="showConflictWarning"
        class="alert alert-warning"
        x-cloak
    >
        This item was modified by another user.
        We've refreshed it with the latest version.
    </div>

    <!-- Your component content -->
</div>

<script>
component.$el.addEventListener('tetra:call-conflict', () => {
    component.showConflictWarning = true;
    setTimeout(() => {
        component.showConflictWarning = false;
    }, 5000);
});
</script>
```

## Testing Offline Mode

To test the offline queue functionality without restarting your server:

### Using Browser DevTools

**Firefox:**
1. Open DevTools (F12)
2. Go to Network tab
3. Select "Offline" from the Throttling dropdown
4. Perform actions (delete items, add items, etc.)
5. Switch back to "No throttling"

**Chrome:**
1. Open DevTools (F12)
2. Go to Network tab
3. Select "Offline" from the Throttling dropdown
4. Perform actions
5. Switch back to "No throttling"

### Using JavaScript Console

```javascript
// Simulate offline mode
Tetra.ws.close()

// Perform your actions

// Reconnect (automatic after 3 seconds, or manually):
Tetra.ensureWebSocketConnection()
```

!!! warning "Don't Restart Server During Testing"
    Restarting the Django server during offline testing will regenerate component IDs and encryption keys, causing queued calls to fail. Use browser DevTools offline mode instead.

## Implementation Details

### Retry Logic

Failed calls (500+ errors or network errors) are automatically retried:

- **Initial retry**: Attempted when connection is restored
- **Retry delay**: 2 seconds between retry attempts
- **Queue position**: Server errors go to back of queue, network errors to front
- **Maximum retries**: No limit (retries until success or permanent failure)

### Snapshot Storage

Snapshots are stored in memory only:

- **Lifetime**: From queue time until successful reconciliation or permanent failure
- **Size**: Includes full component state + HTML (can be large for complex components)
- **Cleanup**: Automatically removed after processing

### Performance Considerations

The offline queue is designed for moderate usage:

- **Queue size**: No hard limit, but large queues (100+ items) may impact performance
- **Snapshot size**: Each snapshot includes full component HTML, consider this for large components
- **Lookup speed**: Component lookup by key is O(n) where n = number of components on page

## Related Documentation

- [Online/Offline Status](online-status.md) - Monitor connection status
- [Events](events.md) - All Tetra events
- [Reactive Components](reactive-components.md) - WebSocket-based components
- [State Security](state-security.md) - How encrypted state works
