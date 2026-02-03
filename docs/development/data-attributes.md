# Internal Data Attributes in Tetra

Tetra uses specialized `x-data-*` attributes to manage the synchronization of component state between the Django server and the Alpine.js client, particularly during re-renders and DOM morphing. These attributes are primarily handled in the `ComponentRenderer` on the server and `_updateHtml()` (using `Alpine.morph`) on the client.

### 1. `x-data`
This is the standard Alpine.js attribute used to initialize component data.
- **Server Side**: In `ComponentRenderer.render`, it is set either to the component's initialization function (e.g., `my_component('{"key": "value"}')`) during the initial page load or left empty when updating/maintaining state.
- **Client Side**: Alpine.js uses this to create the reactive scope for the component.

### 2. `x-data-maintain`
This attribute is used when the server wants the client to keep its current JavaScript state entirely, even if the HTML is being replaced.
- **Server Side**: Set by `update_html(include_state=False)` or when `RenderDataMode.MAINTAIN` is used. This happens when the server re-renders the HTML (e.g., due to a change in non-reactive attributes) but doesn't want to overwrite the client's current data.
- **Client Side**: During `Alpine.morph` (in `tetra.core.js`), if `toEl` (the new element) has `x-data-maintain`, Tetra copies the `x-data` from the `el` (existing element) to `toEl`. This ensures that any client-side changes (like typing in an input) are not lost when the HTML is refreshed.

### 3. `x-data-update` and `x-data-update-old`
These attributes work together to perform a "smart merge" of data from the server into the client, preventing the loss of concurrent client-side changes.
- **Server Side**: Set by `update()` or `update_html(include_state=True)` (mode `UPDATE`).
    - `x-data-update`: Contains the **new** state of the component on the server.
    - `x-data-update-old`: Contains the **previous** state of the component (what the server *thought* the client had before the current operation).
- **Client Side**: Inside the `Alpine.morph` lifecycle:
    1. It decodes both the new data and the "old" data.
    2. It iterates through the keys in the new data.
    3. **Collision Detection**: For each key, it compares the current client value with `old_data`. If the client value has changed relative to `old_data`, Tetra assumes the user has modified it locally and **skips** the update for that specific field to avoid overwriting user input.
    4. Otherwise, it updates the client's component property with the new server value.
    5. Finally, it removes these temporary attributes and ensures Alpine's `x-data` is synced.

### Summary Table

| Attribute           | Purpose             | Logic                                                                        |
|:--------------------|:--------------------|:-----------------------------------------------------------------------------|
| `x-data`            | Initialization      | Standard Alpine.js data initialization.                                      |
| `x-data-maintain`   | Preservation        | Keeps the client-side state exactly as is during an HTML replacement.        |
| `x-data-update`     | Smart Merge         | Provides new server values for component properties.                         |
| `x-data-update-old` | Conflict Resolution | Used to detect if the client has changed a value since the last server sync. |

These attributes allow Tetra to provide a "single-page app" feel where HTML can be refreshed from the server without causing input flicker or losing the user's current focus and data.