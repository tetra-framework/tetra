---
title: Saved Server State and Security
---

# Saved Server State and Security

When a component is rendered, as well as making its public state available as JSON to the client, it saves its server state so that it can be resumed later. This is done using the builtin Python Pickle toolkit. The "Pickled" state is then encrypted using 128-bit AES and authenticated with HMAC via [Fernet](https://cryptography.io/en/latest/fernet/) using a key derived from your Django settings `SECRET_KEY` and the user's session id using [HKDF](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#hkdf).

This state is then sent to the client and resubmitted back to the server for unpickling on further requests via public methods. Each time the state changes on the server a new pickled state is created and sent to the client.

By using Pickle for the serialisation of the server state we are able to support a very broad range of object types, effectively almost anything.

It is essential that the Django `SECRET_KEY` is kept secure. It should never be checked into source controls, and ideally be stored securely by a secrets management system.

## Security Safeguards

To protect against potential security vulnerabilities, Tetra implements strict type checking during the unpickling process. Only types from a predefined "safe list" are allowed to be unpickled. This prevents arbitrary code execution even if an attacker manages to forge an encrypted state token.

### Safe Types

The following types are allowed by default:

**Built-in types:**
- Basic types: `str`, `int`, `float`, `bool`, `bytes`, `bytearray`, `complex`, `range`, `type`, `NoneType`
- Collections: `list`, `dict`, `set`, `frozenset`, `tuple`
- Utilities: `slice`, `object`, `Ellipsis`, `NotImplementedType`

**Standard library types:**
- `datetime`: `datetime`, `date`, `time`, `timedelta`, `timezone`
- `decimal`: `Decimal`
- `collections`: `OrderedDict`, `defaultdict`, `Counter`, `deque`
- `pathlib`: `PurePath`, `PosixPath`, `WindowsPath`
- `uuid`: `UUID`

**Django types:**
- `django.utils.safestring`: `SafeString`, `SafeData`, `SafeText`
- Django models (automatically detected)
- Django forms
- Django QuerySets (handled via custom picklers)

**Tetra types:**
- All Tetra component classes
- Custom types registered via the `@register_pickler` decorator

### Custom Type Serialization

If you need to serialize a type that is not in the safe list, you must register a custom pickler for it. See the implementation of `PickleModel`, `PickleQuerySet`, or `PickleFieldFile` in `src/tetra/state.py` for examples.

!!! warning
    If you attempt to use a variable type that is not in the safe list and doesn't have a custom pickler, you will receive a `StateException` during unpickling with a message like: `"Unpickling blocked: 'module.ClassName' is not in the allowed list."`

    This is a security feature, not a bug. To resolve this, either:
    1. Use a type that is already in the safe list
    2. Register a custom pickler for your type using `@register_pickler`

As this encrypted server state was generated after the component had been passed its arguments, and after any view based authentication, it holds onto that authentication when resumed later. It is, in effect, an authentication token allowing the user to continue from that state at a later point in time. It is also possible to do further authentication within the `load()` method, or any other public method.

## State optimizations

A number of optimizations have been made to ensure that the Pickled state is efficient and doesn't become stale. These include:

- Models are saved as just a reference to the model type and the primary key. They are then retrieved from the database when unpickling. This ensures that they always present the latest data to your public methods.

- QuerySets are saved in raw query form, not including any of the results. After unpickling, they are then lazily run to retrieve results from the database when required.

- Template Blocks passed to a component are saved as just a reference to where they originated. This is almost always possible. It includes blocks defined within a component's template, or blocks in templates loaded using a Django built-in template loader.

- When a component runs its `load` method, it tracks what properties are set. These are then excluded from the data when pickling. The `load` method is re-run after unpickling using the same arguments it was originally passed, or updated arguments if it is being resumed as a child component.

## Stale State Handling

In multi-client scenarios, a component's state can become stale when database objects it references are deleted or modified by another client. Tetra handles this gracefully:

**What happens when state becomes stale:**

1. When a component method is called, Tetra attempts to restore the component state by calling its `load()` method
2. If the `load()` method fails because referenced objects no longer exist (e.g., `DoesNotExist` error), a `StaleComponentStateError` is raised
3. The server returns a **410 Gone** HTTP status with error code `"StaleComponentState"`
4. The client automatically removes the stale component from the DOM
5. A `tetra:component-stale` event is dispatched for custom handling if needed

**Example scenario:**
```python
class TodoItem(ReactiveComponent):
    def load(self, todo_id):
        # This will raise DoesNotExist if another client deleted the todo
        self.todo = Todo.objects.get(pk=todo_id)

    @public
    def delete_item(self):
        self.todo.delete()
        self.client._removeComponent()
```

If Client A deletes a todo while Client B still has it open (and is out of sync), Client B's component will be gracefully removed when they try to interact with it.

**Custom handling:**

You can listen for the `tetra:component-stale` event to provide custom feedback to users:

```html
<div @tetra:component-stale.document="handleStaleComponent($event)">
    <!-- Your component -->
</div>
```

```javascript
function handleStaleComponent(event) {
    const message = event.detail.error.message;
    // Show a user-friendly notification
    alert(message);
}
```

See [Events](events.md#tetracomponent-stale) for more information about the `tetra:component-stale` event.