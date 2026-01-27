# Tetra Client-Server Protocol Specification

## Overview
This document formalizes the communication protocol between Tetra's client-side drivers (e.g., Alpine.js) and the Django server. Tetra uses a hybrid approach using both HTTP (for component method calls and initial renders) and WebSockets (for real-time updates and notifications).

The protocol is inspired by **JSON-RPC 2.0** but adapted to support Tetra's specific requirements for state management, server-side callbacks, and UI metadata (styles/scripts).

Current Status: **Phase 1 (HTTP) and Phase 2 (WebSockets) Implemented.**

---

## 1. Transport Mechanisms

### 1.1 HTTP (Method Calls)
- **Method:** `POST`
- **Content-Type:** `application/json` or `multipart/form-data` (for file uploads)
- **Endpoint:** Component-specific URL
- **Headers:**
    - `T-Request: true`: Identifies the request as a Tetra protocol request.
    - `X-CSRFToken`: Standard Django CSRF protection.
    - `T-Current-URL`: The current URL of the page in the browser.

### 1.2 WebSockets (Real-time)
- **Protocol:** JSON-based messages over WebSocket using the Unified Protocol envelope.
- **Endpoint:** `/ws/tetra/`

---

## 2. Request Structure (Client to Server)

### 2.1 Component Method Call (HTTP)
A request to execute a public method on a component.

```json
{
  "protocol": "tetra-1.0",
  "id": "req-123",
  "type": "call",
  "payload": {
    "component_id": "comp-unique-id",
    "method": "my_public_method",
    "args": ["arg1", 42],
    "state": {},
    "encrypted_state": "...",
    "children_state": {}
  }
}
```

- `protocol`: Version of the Tetra protocol (currently `"tetra-1.0"`).
- `id`: Unique request identifier (for matching responses).
- `type`: Message type (currently `"call"`).
- `payload`: Object containing request-specific data.

### 2.2 WebSocket Messages (Client to Server)

#### Subscribe
```json
{
  "type": "subscribe",
  "group": "my-update-group"
}
```

#### Unsubscribe
```json
{
  "type": "unsubscribe",
  "group": "my-update-group"
}
```

---

## 3. Response Structure (Server to Client)

Every message from the server follows a consistent top-level structure.

```json
{
  "protocol": "tetra-1.0",
  "id": "req-123",
  "type": "call.response",
  "payload": {
    "result": "Success message"
  },
  "metadata": {
    "js": ["/static/tetra/comp.js"],
    "styles": ["/static/tetra/comp.css"],
    "messages": [
      {"level": "success", "message": "Saved!", "uid": "uuid"}
    ],
    "callbacks": [
      {
        "callback": ["_updateHtml"], 
        "args": ["<div tetra-component=\"MyComponent\">...</div>"]
      }
    ]
  }
}
```

### 3.2 WebSocket Messages (Server to Client)

#### Subscription Response
Standardizes the response to subscription/unsubscription requests.

```json
{
  "protocol": "tetra-1.0",
  "type": "subscription.response",
  "payload": {
    "group": "my-update-group",
    "status": "subscribed",
    "message": ""
  },
  "metadata": {}
}
```

#### Component Update
Standardizes real-time updates to also use the unified envelope.

```json
{
  "protocol": "tetra-1.0",
  "type": "component.update_data",
  "payload": {
    "group": "my-update-group",
    "data": { "title": "New Title" }
  },
  "metadata": {}
}
```

#### Notify
```json
{
  "protocol": "tetra-1.0",
  "type": "notify",
  "payload": {
    "group": "my-group",
    "event_name": "tetra:custom-event",
    "data": {}
  },
  "metadata": {}
}
```

---

## 4. State Management & HTML Updates
Tetra relies on "state-ful" communication where the client sends its current knowledge of the component's state, and the server returns the updated state or HTML.

1. **Client sends `state`**: Encoded JSON representing component public attributes.
2. **Server reconstructs component**: Uses `state` to populate the component instance.
3. **Server executes method**: Modifies attributes or performs actions.
4. **HTML Generation**: If the method or component triggers an update (default for `@public` methods), the server renders the component template to HTML.
5. **Server returns `callbacks`**: The response includes one or more callbacks (e.g., `_updateHtml`) containing the freshly rendered HTML or `_updateData` containing the updated state.
6. **Client applies update**: The client-side driver receives the callback and updates the DOM with the new HTML or synchronizes its internal Alpine.js state.

---

## 5. Specialized Responses

### 5.1 FileResponse
When a component method returns a Django `FileResponse`, Tetra returns the file directly to the browser.
- **Headers**: 
    - `Content-Disposition: attachment; filename="..."`
- **Behavior**: The client-side driver detects the `attachment` disposition and triggers a browser download.

### 5.2 Redirects
Redirects are handled via the `_redirect` callback in the `metadata.callbacks` list.
```json
{
  "metadata": {
    "callbacks": [
      {
        "callback": ["_redirect"],
        "args": ["/new-url"]
      }
    ]
  }
}
```

### 5.3 Asset Injection
Styles and scripts required by the components are included in the `metadata`.
- `metadata.js`: List of URLs to JavaScript files to be loaded.
- `metadata.styles`: List of URLs to CSS files to be loaded.
The client-side driver ensures these are loaded exactly once before applying other updates.

---

## 6. Error Handling

Errors use a standardized structure within the unified protocol response. When `success` is `false`, an `error` object is provided.

```json
{
  "protocol": "tetra-1.0",
  "id": "req-123",
  "success": false,
  "error": {
    "code": "ValueError",
    "message": "Invalid input provided"
  },
  "metadata": {
    "messages": [],
    "callbacks": []
  }
}
```

- `code`: The exception class name or a specific error code.
- `message`: A human-readable error message.

The client-side driver emits a `tetra:method-error` CustomEvent when such a response is received, allowing for global or component-specific error handling.

---

## 6. History & Status
Starting with Tetra 0.8.1, the HTTP method calls have been unified into a JSON-based, unified protocol. 
