---
title: Routing
---

# Routing

Tetra includes a built-in routing system that allows you to create a "Single Page Application (SPA)" experience within Django. It enables dynamic component switching and URL updates without full page reloads, while keeping the routing server side.

The routing system consists of three main components: `Router`, `Link`, and `Redirect`.

## `Router` Component

The `Router` component is responsible for matching the current URL path to a specific Tetra component and rendering it.

### Usage

To use the router, create a subclass of `Router` and define its `routes` attribute. The `routes` dictionary maps URL path patterns to the full names of the components you want to render.

```python
from tetra import Router, Library

library = Library("my_app")

@library.register
class MyRouter(Router):
    routes = {
        "/": "my_app.Home",
        "/about": "my_app.About",
        "/user/(?P<id>\\d+)": "my_app.UserProfile",
    }
```

Then, include your router in a Django template:

```html
{% load tetra %}
...
{% MyRouter / %}
```

### Route Matching

The router supports both exact string matches and regular expressions:

1.  **Exact Match**: `"/about": "my_app.About"` matches only exactly `/about`.
2.  **Regex Match**: `"/user/(?P<id>\\d+)": "my_app.UserProfile"` uses regex to match paths.

When a route is matched, the router updates its `current_component` and renders it using the dynamic component syntax `{% component "=current_component" / %}`.

### `Router` Attributes

- `routes`: A dictionary mapping paths (strings or regex) to component names.
- `current_component`: (Public) The name of the currently active component.
- `current_path`: (Public) The current URL path being handled by the router.

## `Link` Component

The `Link` component is a replacement for standard `<a>` tags for internal navigation. It intercepts clicks, updates the browser's URL using `pushState`, and notifies the `Router` to switch views.

### Usage

```html
{% Link to="/about" label="About Us" / %}
```

Or using slots for the label:

```html
{% Link to="/" %}
    <img src="logo.png" alt="Home">
{% endLink %}
```

### `Link` Attributes

- `to`: The target URL path.
- `label`: The text to display inside the link.
- `active_class`: The CSS class to apply when the current path matches the link's `to` path. Defaults to `"active"`.
- other HTML tags can be added via the `attrs:` keyword: `{% Link to="/" attrs: class="nav-link" %}`

The `Link` component automatically applies the `active_class` (default: "active")  when the current component matches the `to` path.

## `Redirect` Component

The `Redirect` component triggers a navigation to a specified path as soon as it is rendered. This is useful for conditional redirects within your component logic.

### Usage

```html
{% Redirect to="/login" / %}
```

## Complete Example

Here is how you might set up a simple application with routing.

**1. Define your view components:**

```python
# my_app/components.py
from tetra import Component, Library

lib = Library("my_app")

@lib.register
class Home(Component):
    template = "<div><h1>Home Page</h1><p>Welcome to our SPA!</p></div>"

@lib.register
class About(Component):
    template = "<div><h1>About Us</h1><p>We love Tetra!</p></div>"
```

**2. Create the Router:**

```python
# my_app/components.py
from tetra.router import Router

@lib.register
class AppRouter(Router):
    routes = {
        "/": "my_app.Home",
        "/about": "my_app.About",
    }
```

You can also collect routes from different apps, or use other patterns:
```python
# my_app/components.py
from other_app.routes import routes as other_app_routes
from third_app.routes import routes as third_app_routes

@library.register
class AppRouter(Router):
    routes = {
        **other_app_routes,
        **third_app_routes,
        "/": "project.Home",
    }
```

Even plugins can be used, e.g., by using [gdaps](https://gdaps.readthedocs.org) or other plugin frameworks.

**3. Use them in your base template:**

```html
{% load tetra %}
<!DOCTYPE html>
<html>
<head>
    {% tetra_styles %}
</head>
<body>
    <nav>
        {% Link to="/" label="Home" / %}
        {% Link to="/about" label="About" / %}
    </nav>

    <main>
        {% AppRouter / %}
    </main>

    {% tetra_scripts %}
</body>
</html>
```

## How it Works

1.  **Browser Navigation**: The `Router` listens for `popstate` events on the `window`. When you use the browser's back/forward buttons, the router detects the URL change and updates the component.
2.  **Internal Links**: The `Link` component prevents the default browser navigation and instead dispatches a `tetra:navigate` event.
3.  **Dynamic Swapping**: The `Router` receives the `tetra:navigate` event, updates the browser URL, matches the new path against its `routes`, and swaps the displayed component.
