# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tetra is a full-stack component framework for Django using Alpine.js. It combines Python, HTML, CSS, and JavaScript into encapsulated components with server-side state management and inplace DOM updates.

## Common Commands

```bash
make setup        # Install dependencies with uv
make setup-dev    # Install + playwright browsers for E2E tests
make test         # Run pytest
make check        # Run ruff linter
make build-js     # Build JavaScript with esbuild
make build        # Build Python package
make doc          # Build documentation (MkDocs)
make doc-dev      # Serve docs locally
```

## Architecture

### Core Components

- **Component** (`src/tetra/components/base.py`): Base class combining Python logic, HTML template, CSS, and JavaScript
- **BasicComponent**: Simplified component without form handling
- **FormComponent**: Extends Component with Django form capabilities
- **ModelFormComponent**: Django ModelForm integration (needs form_class + object)
- **ReactiveComponent** (`src/tetra/components/reactive.py`): WebSocket-based reactive updates (requires Django Channels)
- **ReactiveModel** (`src/tetra/models.py`): Abstract model that broadcasts changes to components via WebSocket

### State Management

- **Resumable server state**: Encrypted state preserved between method calls
- **Public shared state**: Exposed to frontend via Alpine.js data bindings using `@public` decorator
- **Protocol**: Custom `tetra-1.0` protocol using HTTP POST for method calls and WebSockets for reactive updates

### Component Libraries & File Structure

Every component belongs to a **Library**. Libraries are discovered automatically from `<app>.components.<library_name>`.

#### Inline components (simple, small)
```
myapp/
  components/
    default.py          ← Put multiple component classes directly here
    widgets.py          ← Another library named "widgets"
```

#### Directory-style components (with separate HTML/JS/CSS files)
```
myapp/
  components/
    default/
      __init__.py       ← Can contain inline component classes
      my_calendar/
        __init__.py     ← Component class (ONE per directory)
        my_calendar.html  ← External template
        my_calendar.js    ← External JavaScript
        my_calendar.css   ← External CSS
```

**Rule:** Directory-style component modules may contain only ONE component class. Inline library modules can contain multiple.

### Django Integration

1. Add `'tetra'` to `INSTALLED_APPS`
2. Add `'tetra.middleware.TetraMiddleware'` to `MIDDLEWARE`
3. Include Tetra URLs: `path("", include("tetra.urls"))`
4. Use `{% load tetra %}` template tag
5. Render with `{% ComponentClassName / %}` for default library or `{% library.ComponentClassName / %}`

### JavaScript/Build Pipeline

- JavaScript source in `src/tetra/js/`
- Built assets in `src/tetra/static/tetra/js/`
- Uses esbuild for bundling
- Alpine.js with Morph plugin for inplace updates

### Testing

- pytest with pytest-django
- E2E tests use pytest-playwright
- Test apps in `tests/apps/`

---

## Creating Components

### Minimal Component

```python
from tetra import Component, public

class Counter(Component):
    count = public(0)

    @public
    def increment(self):
        self.count += 1

    template = """
    <div>
        <span x-text="count"></span>
        <button @click="increment()">+1</button>
    </div>
    """
```

### Full-Featured Component

```python
from sourcetypes import django_html, javascript, css
from tetra import Component, public

class TodoItem(Component):
    # Public attributes — available in both Python and Alpine.js
    title = public("")
    done = public(False)

    # Private attributes — server-only, saved with state
    todo = None

    def load(self, todo, *args, **kwargs):
        """Called on init AND after state resume."""
        self.todo = todo
        self.title = todo.title
        self.done = todo.done

    @public.watch("title", "done").debounce(200)
    def save(self, value, old_value, attr):
        """Auto-called when watched public attrs change."""
        self.todo.title = self.title
        self.todo.done = self.done
        self.todo.save()

    @public(update=False)
    def delete_item(self):
        """update=False skips re-render."""
        self.todo.delete()
        self.client._removeComponent()

    template: django_html = """
    <div>
        <input type="checkbox" x-model="done">
        <input type="text" x-model="title">
    </div>
    """

    script: javascript = """
    export default {
        init() { ... }
    }
    """

    style: css = """
    .todo-strike { text-decoration: line-through; }
    """
```

---

## Key Concepts

### `public()` — Public Attributes

```python
name = public("default")       # Available in Python AND Alpine.js
count = public(0)
items = public([])
```

Values must be JSON-serializable (extended: `datetime`, `date`, `time`, `set`, `Decimal`).

### `@public` — Public Methods

```python
@public                              # Re-renders component after call (default)
def my_method(self): ...

@public(update=False)                # No re-render
def fire_and_forget(self): ...

@public.watch("attr1", "attr2")      # Auto-called on attr change
def on_change(self, value, old_value, attr): ...

@public.watch("query").debounce(300) # Debounced watcher
def search(self, value, old_value, attr): ...

@public.watch("x").throttle(500, trailing=True)
def throttled(self, value, old_value, attr): ...

@public.listen("keyup.enter")        # Subscribe to DOM event
def enter_pressed(self, event_detail): ...

@public.listen("custom-event.window") # Global event listener
def global_handler(self, event_detail): ...
```

### `.store()` — Alpine.js Global Store Sync

```python
theme = public("light").store("settings")
# Syncs with Alpine.store('settings').theme bidirectionally
```

### `load()` Method

- Called on **initial render** and **after state resume**
- Arguments come from template tag: `{% MyComp arg1 kwarg=val / %}`
- Arguments are saved with state for resume
- **Attributes set in `load()` are NOT saved** — they are re-fetched each time
- Use for database queries, computed values

### `client` API — Server-to-Client Callbacks

```python
@public(update=False)
def my_method(self):
    self.client.myJsMethod("arg")        # Call JS method
    self.client._redirect("/url")         # Redirect browser
    self.client._removeComponent()        # Remove from DOM
    self.client._dispatch("event", data)  # Dispatch Alpine event
    self.client._updateData({"key": val}) # Update specific data
    self.client._parent.method()          # Call parent component method
```

### Built-in Server Methods

```python
self.update()                    # Force re-render
self.update_data()               # Send public data without re-render
self.replace_component()         # Full DOM replacement (loses client state)
self.push_url("/new-url")        # Push URL to browser history
self.replace_url("/new-url")     # Replace URL without history entry
self.update_search_param("q", "val")  # Update URL query param
```

### `calculate_attrs(component_method_finished: bool)`

Hook called before and after user interactions:

```python
def calculate_attrs(self, component_method_finished):
    if component_method_finished:
        self.total = sum(item.price for item in self.items)
```

---

## Templates

### Template Tag Syntax

```django
{% load tetra %}

{# Self-closing #}
{% MyComponent arg1 kwarg="val" / %}

{# With content/slots #}
{% MyComponent %}
  Content goes to default slot
{% /MyComponent %}

{# With library prefix #}
{% widgets.Button label="Click" / %}

{# Dynamic component name #}
{% component =variable_name / %}
```

### Passing Data

```django
{# Arguments → load() method #}
{% MyComp "positional" named=context_var / %}

{# HTML attributes → attrs dict #}
{% MyComp attrs: class="red" id="main" / %}

{# Context variables → template context only (NOT saved with state) #}
{% MyComp context: user other_var / %}
{% MyComp context: __all__ / %}
```

### Slots

```django
{# In component template: #}
<div>
  {% slot default %}Fallback{% endslot %}
  {% slot sidebar %}{% endslot %}
</div>

{# Usage: #}
{% Card %}
  {% slot sidebar %}Nav{% endslot %}
  Main content
{% /Card %}
```

### Attribute Tag (`...`)

```django
<div {% ... attrs class="base-class" %}>
```

### `livevar` Tag

```django
{% livevar first_name %}
{% livevar count tag="strong" %}
```

### `tetra` Context Variable

```django
{{ tetra.current_url }}
{{ tetra.current_url_path }}
{{ tetra.current_url_full_path }}
```

### `_extra_context`

```python
class MyComp(BasicComponent):
    _extra_context = ["user", "some_var"]
    _extra_context = "__all__"
```

---

## Two-Way Bindings (Parent-Child)

You can create two-way bindings between child and parent component attributes using `:` prefix:

```django
{# Child's "result" binds to parent's "selected_name" (two-way) #}
{% SearchComponent :result=selected_name / %}

{# Shorthand - both use same name #}
{% SearchComponent :name / %}

{# Explicit bind: prefix (same as above) #}
{% SearchComponent bind:result=selected_name / %}

{# Multiple bindings #}
{% SearchComponent :result=a :query=b / %}
```

### How it works

1. Template parser extracts binding info (`{child_attr: parent_attr}`)
2. Server includes `__bindings` and `__parentKey` in render data
3. Client-side JS sets up two watchers: child→parent and parent→child
4. Changes sync immediately without server round-trip

---

## FormComponent

```python
from django import forms
from tetra.components import FormComponent, public

class PersonForm(forms.Form):
    first_name = forms.CharField(max_length=25, initial="Jean-Luc")
    last_name = forms.CharField(max_length=25)

class PersonEditor(FormComponent):
    form_class = PersonForm

    template = """
    <div>
        <input type="text" x-model="first_name">
        <input type="text" x-model="last_name">
        <button @click="submit()">Save</button>
        {% for error in form_errors %}<p>{{ error }}</p>{% endfor %}
    </div>
    """

    def form_valid(self):
        # Handle valid form
        pass

    def form_invalid(self):
        # Handle invalid form
        pass
```

### ModelFormComponent

```python
class PersonEditor(ModelFormComponent):
    form_class = PersonModelForm
    object: Person = None

    def load(self, pk, *args, **kwargs):
        self.object = Person.objects.get(pk=pk)
```

### DynamicFormMixin — Dependent Fields

```python
class CarEditor(DynamicFormMixin, FormComponent):
    form_class = CarForm

    @public.watch("make")
    def make_changed(self, value, old_value, attr):
        pass

    def get_model_queryset(self):
        return CarModel.objects.filter(make=self.make)

    def get_engine_type_disabled(self):
        return self.make == "Tesla"
```

Methods: `get_<field>_queryset()`, `get_<field>_disabled()`, `get_<field>_hidden()`, `get_<field>_required()`

---

## ReactiveComponent (WebSocket Push)

Requires Django Channels + Redis + ASGI server.

```python
from tetra import ReactiveComponent, public

class ChatMessage(ReactiveComponent):
    message = public("")
    subscription = "chat.room.general"

    def get_subscription(self):
        return f"chat.room.{self.room_id}"
```

### Pushing Data from Server

```python
from tetra.dispatcher import ComponentDispatcher
from asgiref.sync import async_to_sync

async_to_sync(ComponentDispatcher.data_changed)(
    "chat.room.general", data={"message": "Hello!"}
)

async_to_sync(ComponentDispatcher.notify)(
    group="broadcast", event_name="tetra:alert", data={"msg": "Update!"}
)
```

### Auto-subscribed groups

- `auth.user.{user_id}`
- `session.{session_key}`
- `broadcast`

---

## ReactiveModel

```python
from tetra.models import ReactiveModel

class ChatMessage(ReactiveModel):
    class Tetra:
        fields = ["content", "author"]

    content = models.TextField()
    author = models.CharField(max_length=100)
```

---

## Routing

### Basic Router

```python
from tetra.router import route

@library.register
class AppRouter(Router):
    routes = [
        route("", Home, name="home"),
        route("about/", About, name="about"),
        route("user/<int:id>/", UserProfile, name="user-detail"),
    ]

    template = """
    <div>
        <nav>...</nav>
        <main>{% router_view %}</main>
    </div>
    """
```

### URL Parameters

```python
route("user/<int:id>/", UserProfile)
route("post/<slug:slug>/", PostDetail)

# Access in component:
user_id = self.request.tetra.route_params.get("id")
```

### Named Routes

```python
reverse("home")
reverse("user-detail", id=123)
reverse("admin:dashboard")
```

### Link Component

```django
{% Link to="/about" label="About" / %}
{% Link to="/about" %}Custom{% /Link %}
```

---

## Component Lifecycle (Data Flow)

1. **Class defaults** → attributes set on class body
2. **Resumed state** → decrypted previous state (if resuming)
3. **`load()`** → called with saved args
4. **Client data** → public attrs updated from browser
5. **`calculate_attrs(False)`** → pre-method hook
6. **Public method executes**
7. **`calculate_attrs(True)`** → post-method hook
8. **Render** → template rendered, state encrypted, HTML sent to client

---

## State & Security

- Component state: **pickled → gzipped → signed (HMAC) → encrypted (Fernet)** per session
- State tokens expire after 24h (configurable: `TETRA_STATE_MAX_AGE`)
- Django Models stored as `(class, pk)` references

---

## Client-Side Events

- `tetra:before-request` / `tetra:after-request`
- `tetra:component-updated`
- `tetra:component-data-updated`
- `tetra:component-before-remove`
- `tetra:new-message`

---

## Common Patterns

### Component in a loop (always use `key`!)

```django
{% for item in items %}
    {% ItemComponent item=item key=item.id / %}
{% endfor %}
```

### Parent-child communication

```python
# Child dispatches event
@public(update=False)
def notify_parent(self):
    self.client._dispatch("item-saved", {"id": self.item.id})

# Parent listens
@public.listen("item-saved")
def on_item_saved(self, event_detail): ...
```

---

## Key Technologies

- Python 3.12+
- Django 5.2+
- Alpine.js
- esbuild
- Django Channels (optional)
- uv (package manager)
