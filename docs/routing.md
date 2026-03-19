---
title: Routing
---

# Routing

!!! warning
    SPA routing is currently **highly experimental** and not meant to be used in a production environment. It is subject to significant changes and potential removal in future versions.

Tetra includes a built-in routing system that allows you to create a "Single Page Application (SPA)" experience within Django. It enables dynamic component switching and URL updates without full page reloads, while keeping the routing server side.

The routing system consists of three main components: `Router`, `Link`, and `Redirect`.

## `Router` Component

The `Router` component is responsible for matching the current URL path to a specific Tetra component and rendering it.

### Basic Usage

Tetra supports routing by using `Router` subclasses that define one or more `tetra.router.route` entries in a `routes` property.
It uses Django's URL pattern syntax and supports nested routing:

```python
from tetra import Library
from tetra.router import route
from tetra.components.default.router import Router
from my_app.components import Home, About, UserProfile

library = Library("library", "my_app")


@library.register
class MyRouter(Router):
    routes = [
        route("", Home),
        route("about/", About),
        route("user/<int:id>/", UserProfile),
    ]
```

Then, include your router in a Django template:

```html
{% load tetra %}
...
{% MyRouter / %}
```

### Custom Router Templates

By default, the `Router` renders matched components in a simple `<div>` wrapper. You can customize the router's layout by defining a custom `template` that includes the `{% router_view %}` tag to mark where the matched component should render:

```python
@library.register
class MyRouter(Router):
    routes = [
        route("", Home),
        route("about/", About),
        route("user/<int:id>/", UserProfile),
    ]

    template = """
    <div class="app-layout">
        <header>
            <h1>My App</h1>
            <nav>
                {% Link to="/" %}Home{% /Link %}
                {% Link to="/about/" %}About{% /Link %}
            </nav>
        </header>
        <main>
            {% router_view %}  <!-- Matched component renders here -->
        </main>
        <footer>
            <p>&copy; 2026 My App</p>
        </footer>
    </div>
    """
```

The `{% router_view %}` template tag is where the matched route component will be rendered. This allows you to:

- Define consistent layouts around your routed content
- Add navigation, headers, or footers at the router level
- Create nested layouts with multiple router levels
- Control exactly where child components appear in the page structure

**Note:** The router automatically handles navigation events (`@popstate.window` and `@tetra:navigate.window`) - you don't need to add these in your custom template.

### URL Parameters

Routes can capture URL parameters which components access via `request.tetra.route_params`:

```python
from tetra import Component

@library.register
class UserProfile(Component):
    user_id: int = 0

    template = "<div>User Profile: {{ user_id }}</div>"

    def load(self, *args, **kwargs):
        # Explicitly get route parameter (secure)
        user_id = self.request.tetra.route_params.get('id')
        if user_id:
            self.user_id = int(user_id)

@library.register
class MyRouter(Router):
    routes = [
        route("user/<int:id>/", UserProfile),
    ]
```

The `<int:id>` pattern captures the ID from URLs like `/user/123/` and makes it available via `request.tetra.route_params['id']`.

**Security Note:** URL parameters are **NOT** automatically passed to `load()` methods to prevent URL manipulation from overriding component parameters. Components must **explicitly** access route parameters via `request.tetra.route_params`.

### Nested Routing

Tetra supports two patterns for nested routing: **explicit** and **delegated**. Both patterns work seamlessly with custom router templates and the `{% router_view %}` tag.

#### Explicit Nested Routing (Recommended for Simple Apps)

The parent router defines all child and grandchild routes:

```python
@library.register
class MyRouter(Router):
    routes = [
        route("", Home),
        route("patient/<int:patient_id>/", PatientView,
              children=[
                  route("bp/", BloodPressureView),
                  route("lab/", LabResultsView),
              ]),
    ]
```

In this pattern:
- `/patient/123/` renders `PatientView` with `patient_id=123` available via `request.tetra.route_params`
- `/patient/123/bp/` renders `BloodPressureView` with `patient_id=123` accessible the same way
- URL parameters from parent routes are available to child components via `request.tetra.route_params`

Example component implementation:

```python
@library.register
class BloodPressureView(Component):
    patient_id: int = 0

    def load(self, *args, **kwargs):
        # Access inherited parent route parameter
        patient_id = self.request.tetra.route_params.get('patient_id')
        if patient_id:
            self.patient_id = int(patient_id)
```

#### Delegated Nested Routing (Recommended for Complex Apps)

The parent router delegates to a child `Router` component using the `delegate=True` parameter. This provides clean encapsulation where each router manages its own sub-routes:

```python
@library.register
class PatientRouter(Router):
    """Handles patient sub-routes with custom layout."""
    routes = [
        route("", PatientView),
        route("bp/", BloodPressureView),
        route("lab/", LabResultsView),
    ]

    template = """
    <div class="patient-section">
        <aside>
            <h2>Patient {{ url_params.patient_id }}</h2>
            <nav>
                {% Link to="/patient/{{ url_params.patient_id }}/" %}Overview{% /Link %}
                {% Link to="/patient/{{ url_params.patient_id }}/bp/" %}Blood Pressure{% /Link %}
                {% Link to="/patient/{{ url_params.patient_id }}/lab/" %}Lab Results{% /Link %}
            </nav>
        </aside>
        <section>
            {% router_view %}  <!-- Child route renders here -->
        </section>
    </div>
    """

@library.register
class AppRouter(Router):
    routes = [
        route("", Home),
        route("patient/<int:patient_id>/", PatientRouter, delegate=True),
    ]
```

In this example:

1. URL `/patient/123/bp/` is requested
2. `AppRouter` matches `patient/<int:patient_id>/` with `patient_id=123`
3. `PatientRouter` receives the remaining path `bp/` and `url_params={patient_id: 123}`
4. `PatientRouter` matches `bp/` and renders `BloodPressureView` within its custom layout
5. Final HTML: `AppRouter` layout → `PatientRouter` layout → `BloodPressureView` content

**Benefits of Delegated Routing:**

- **Encapsulation**: Parent router doesn't need to know about grandchild routes
- **Reusability**: Child routers can be used in different parent routers
- **Custom Layouts**: Each router level can define its own layout with `{% router_view %}`
- **Maintainability**: Each feature area has its own router and template
- **URL Parameter Inheritance**: Child routers automatically receive parent URL parameters via `url_params`

**Accessing URL Parameters in Nested Routers:**

In custom router templates, URL parameters are available via the `url_params` context variable:

```django
<!-- In PatientRouter template -->
<h2>Patient {{ url_params.patient_id }}</h2>
<nav>
    {% Link to="/patient/{{ url_params.patient_id }}/bp/" %}Blood Pressure{% /Link %}
</nav>
```

Components rendered by the router access parameters via `request.tetra.route_params` as usual:

```python
class BloodPressureView(Component):
    def load(self, *args, **kwargs):
        patient_id = self.request.tetra.route_params.get('patient_id')
        # URL parameters are inherited from parent routers
```

### The `{% router_view %}` Template Tag

The `{% router_view %}` template tag is used within custom router templates to mark where the matched route component should be rendered. It's similar to Vue.js's `<router-view>` component or React Router's `<Outlet>`.

**Usage in Router Templates:**

```python
@library.register
class AppRouter(Router):
    routes = [...]

    template = """
    <div class="app">
        <nav><!-- navigation --></nav>
        {% router_view %}  <!-- Matched component renders here -->
        <footer><!-- footer --></footer>
    </div>
    """
```

**How it Works:**

- The `Router` component matches the current URL against its routes
- When a match is found, it stores the matched component name in the template context
- The `{% router_view %}` tag renders that matched component
- URL parameters and routing context are automatically passed to the child component

**Nested Routing:**

When routers are nested (router within router), each `{% router_view %}` renders the next level:

```python
# Top-level router
class AppRouter(Router):
    template = """
    <div class="app">
        {% router_view %}  <!-- Renders UserRouter -->
    </div>
    """

# Nested router
class UserRouter(Router):
    template = """
    <div class="user-section">
        <nav><!-- user navigation --></nav>
        {% router_view %}  <!-- Renders UserProfile or UserPosts -->
    </div>
    """
```

URL `/users/johnny/posts/` would render:
```
AppRouter layout
  └─ UserRouter layout
      └─ UserPosts component
```

### Route Helper Functions

- `route(pattern, component, children=None, delegate=False)` - Create a route with Django's path syntax
- `path(pattern, component, routes=None)` - Alias for `route()`
- `re_path(pattern, component, routes=None)` - Create a route with regex pattern
- `include(routes)` - Include a list of routes (for readability)

### `Router` Attributes

- `routes`: List of Route objects defining the URL patterns and components
- `namespace`: Optional namespace for route registration (e.g., `"user"`, `"admin"`)
- `template`: Custom template string for the router layout (must include `{% router_view %}` to render matched components)
- `current_component`: (Read-only property) The fully qualified name of the currently matched component
- `current_path`: (Public) The current URL path being handled by the router
- `url_params`: (Public) Dict of URL parameters extracted from the current path (available in templates and passed to child routers)

### `Router` Class Methods

#### `get_routes()`

Class method that returns the list of `Route` objects defined for the router. As default, returns the Router class' `.routes` attribute.

**Usage:**

```python
class AppRouter(Router):
    routes = [
        route("", Home, name="home"),
        route("about/", About, name="about"),
    ]

# Get all routes programmatically
for route_obj in AppRouter.get_routes():
    print(route_obj.name, route_obj.pattern)
```

This method is useful when you need to introspect or programmatically access a router's configured routes, such as for debugging, documentation generation, or dynamic route manipulation.
You can override the `get_routes()` method to return a special list of routes, e.g. from plugins.

### Reversing Routes

Tetra provides global `reverse()` and `reverse_lazy()` functions to generate URL paths from named routes, similar to Django's `reverse()` function. These work with Tetra's component routes and support namespaces.

#### Basic Usage

```python
from tetra.router import route, reverse, reverse_lazy
from tetra.components.default.router import Router


@library.register
class AppRouter(Router):
    routes = [
        route("", Home, name="home"),
        route("about/", About, name="about"),
        route("patient/<int:patient_id>/", PatientView, name="patient-detail"),
    ]


# Global reverse by name
home_url = reverse("home")  # Returns: ""
about_url = reverse("about")  # Returns: "about/"
patient_url = reverse("patient-detail", patient_id=123)  # Returns: "patient/123/"
```

#### Using Namespaces

Routers can define a namespace to organize routes, similar to Django's URL namespaces:

```python
from tetra.router import route, reverse
from tetra.components.default.router import Router


@library.register
class UserRouter(Router):
    namespace = "user"  # Define namespace

    routes = [
        route("", UserHome, name="home"),
        route("profile/<int:user_id>/", UserProfile, name="profile"),
    ]


@library.register
class AdminRouter(Router):
    namespace = "admin"

    routes = [
        route("", AdminDashboard, name="dashboard"),
        route("users/", UserList, name="users"),
    ]


# Reverse with namespace
user_profile = reverse("user:profile", user_id=123)  # Returns: "profile/123/"
admin_dash = reverse("admin:dashboard")  # Returns: ""
```

#### Using in Components

```python
from tetra.router import reverse

@library.register
class MyComponent(Component):
    @public
    def redirect_to_patient(self, patient_id):
        # Generate URL and navigate
        url = reverse("user:profile", user_id=patient_id)
        self.client._dispatch("tetra:navigate", {"path": f"/{url}"})
```

#### Lazy Evaluation

Use `reverse_lazy()` when you need to define URLs at import time:

```python
from tetra.router import reverse_lazy

# At import time - defers evaluation until accessed
SUCCESS_URL = reverse_lazy("user:home")
PROFILE_URL = reverse_lazy("user:profile", user_id=123)
```

#### Named Routes in Nested Routing

Child routes in explicit nested routing can also be named and reversed:

```python
@library.register
class AppRouter(Router):
    namespace = "app"

    routes = [
        route("patient/<int:patient_id>/", PatientView, name="patient", children=[
            route("bp/", BloodPressureView, name="patient-bp"),
        ]),
    ]

# Reverse child route - combines parent and child patterns
bp_url = reverse("app:patient-bp", patient_id=456)
# Returns: "patient/456/bp/"
```

#### Router-Scoped Reverse (Alternative)

Routers also provide class methods for reversing routes within that specific router:

```python
# Class method on specific router
url = AppRouter.reverse("patient-detail", patient_id=123)
lazy_url = AppRouter.reverse_lazy("home")
```

**Note:** Tetra routes are separate from Django's `urlpatterns`. Django's `reverse()` function cannot resolve Tetra routes. Use `tetra.router.reverse()` instead for component routing.

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
from tetra.router import route
from tetra.components.default.router import Router


@lib.register
class AppRouter(Router):
    routes = [
        route("", Home),
        route("about/", About),
    ]
```

You can also collect routes from different apps using `include()`:

```python
# my_app/components.py
from tetra.router import route, include
from tetra.components.default.router import Router
from other_app.routes import routes as other_app_routes
from third_app.routes import routes as third_app_routes


@library.register
class AppRouter(Router):
    routes = [
        route("", Home),
        *other_app_routes,  # Include routes from other apps
        *third_app_routes,
    ]
```

Or define routes in separate files:

```python
# my_app/routes.py
from tetra.router import route
from .components import Home, About, UserProfile

routes = [
    route("", Home),
    route("about/", About),
    route("user/<int:id>/", UserProfile),
]

# my_app/components.py
from tetra.components.default.router import Router
from .routes import routes


@library.register
class AppRouter(Router):
    routes = routes
```

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

## Quick Reference

### URL Pattern Syntax

Tetra uses Django's URL pattern syntax for route-based routing:

| Pattern | Example URL | Description |
|---------|-------------|-------------|
| `<int:id>` | `/user/123/` | Matches integers |
| `<str:name>` | `/user/john/` | Matches strings (no slashes) |
| `<slug:slug>` | `/post/my-post/` | Matches slugs (letters, numbers, hyphens, underscores) |
| `<uuid:id>` | `/item/550e8400-e29b-41d4-a716-446655440000/` | Matches UUIDs |
| `<path:path>` | `/files/docs/readme.txt` | Matches paths (including slashes) |


### Accessing Route Parameters

Route parameters are available via `request.tetra.route_params` (similar to Vue Router's `$route.params`):

```python
class PatientView(Component):
    def load(self, *args, **kwargs):
        # Get route parameter
        patient_id = self.request.tetra.route_params.get('patient_id')

    @public
    def some_action(self):
        # Access anywhere in component methods
        patient_id = self.request.tetra.route_params.get('patient_id')
```

**Template Access:**

```django
<div>
    Patient ID: {{ url_params.patient_id }}
</div>
```

**Security:** Route parameters are **not** automatically injected into `load()` kwargs. This prevents URL manipulation attacks where a malicious URL could override intended component parameters.

### Best Practices

1. **Use custom router templates with `{% router_view %}`** for layouts that wrap routed content (headers, navigation, footers)
2. **Keep routes organized** by defining them in separate `routes.py` files for large applications
3. **Use delegated routing** for complex apps where each section has its own router and layout
4. **Use explicit nested routing** when the parent needs to know all routes (simpler for small apps)
5. **Always explicitly access route parameters** via `request.tetra.route_params` for security
6. **Use browser URL as source of truth** - Tetra uses `request.tetra.current_url_path`, not `request.path`
7. **Leverage `url_params` in router templates** to create dynamic navigation links that reflect current route parameters
8. **Test nested routing carefully** - ensure URL parameters flow correctly through router hierarchies

**When to Use Custom Router Templates:**

- ✅ You need consistent navigation, headers, or footers around routed content
- ✅ Different sections of your app have different layouts (admin vs. user areas)
- ✅ You want to create master-detail layouts with sidebars
- ✅ You need nested routing with multiple layout levels

**When to Use Default Router Template:**

- ✅ Simple apps where routes just swap between full-page components
- ✅ The router is just coordinating components without providing layout
- ✅ Layout is handled by parent Django templates, not the router
