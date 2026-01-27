# Tetra Client-Server Protocol Specification

## Overview
This document formalizes the communication protocol between Tetra's client-side drivers (e.g., Alpine.js) and the Django server. Tetra uses a hybrid approach using both HTTP (for component method calls and initial renders) and WebSockets (for real-time updates and notifications).

The protocol is inspired by **JSON-RPC 2.0** but adapted to support Tetra's specific requirements for state management, server-side callbacks, and UI metadata (styles/scripts).

Current Status: **Phase 1 (HTTP Method Calls) Implemented.**

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
- **Protocol:** JSON-based messages over WebSocket.
- **Endpoint:** `/ws/tetra/`

---

## 2. Request Structure

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
  - `component_id`: Unique ID of the component.
  - `method`: Name of the public method to call.
  - `args`: List of positional arguments.
  - `state`: Current serialized state of the component.
  - `encrypted_state`: Encrypted state for security/integrity.
  - `children_state`: Serialized state of child components.

### 2.2 WebSocket Messages (Client to Server)
Commonly used for subscriptions.

#### Subscribe
```json
{
  "type": "subscribe",
  "group": "my-update-group",
  "component_id": "comp-unique-id",
  "component_class": "MyComponent",
  "auto_update": true
}
```

---

## 3. Response Structure

Tetra is primarily an **HTML-over-the-wire** framework. While the protocol uses JSON for structure and metadata, the primary payload for UI updates is usually rendered HTML.

### 3.1 Success Response (HTTP)
Returned after a successful method call.

```json
{
  "protocol": "tetra-1.0",
  "id": "req-123",
  "success": true,
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

- `payload.result`: The return value of the server-side method.
- `metadata.callbacks`: This is the primary mechanism for "HTML-over-the-wire". The server instructs the client to call specific internal methods with the new HTML or state as arguments.
- `metadata.messages`: Django messages to be displayed on the client.
- `metadata.js` / `metadata.styles`: Dynamic asset injection.

### 3.2 Error Response (HTTP)
Returned when a method call fails.

```json
{
  "protocol": "tetra-1.0",
  "id": "req-123",
  "success": false,
  "error": {
    "code": "method_not_found",
    "message": "Public method 'private_func' not found or not public.",
    "details": {}
  }
}
```

### 3.3 WebSocket Messages (Server to Client)

#### Component Update (HTML or Data)
Standardizes real-time updates to also use callbacks for consistency with HTTP responses.

```json
{
  "type": "component.callback",
  "group": "my-update-group",
  "callback": {
    "method": "_updateHtml",
    "args": ["<div>New real-time content</div>"]
  }
}
```

#### Notify
```json
{
  "type": "notify",
  "group": "my-group",
  "event_name": "custom-event",
  "data": {}
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

## 5. Unified Protocol (Phase 1)
As of Tetra 0.8.1, the HTTP method calls have been unified into this JSON-based protocol. This migration moved metadata that was previously in headers into the JSON response body.

- **Old `T-Messages` header**: Now in `metadata.messages`
- **Old `T-Response` header**: Replaced by checking the `protocol` field.
- **Old `T-Location` / `T-Redirect` headers**: Now handled via callbacks (e.g., `_redirect` or `_pushUrl`).

## 6. Benefits of Formalization
1. **Consistency**: HTTP and WebSockets use the same structured envelope for updates.
2. **Language Agnostic**: Easier to write clients in React, Vue, or even mobile apps.
3. **Type Safety**: Protocol can be defined with JSON Schema or TypeScript interfaces.
4. **Extensibility**: Versioning via the `protocol` field allows for future breaking changes without breaking old clients.
5. **Debuggability**: Structured error codes and messages make it easier to diagnose issues.
