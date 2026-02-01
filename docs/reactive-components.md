---
title: Reactive components
---
# Reactive components

Tetra optionally features async, bidirectional communication using Django channels/websockets. You can use that in "Reactive components" that maintain a long-lasting HTTP connection to the server.

Reactive components can (as the name may suggest) *react* to events that are triggered on the server. This way, a component displayed on multiple clients can synchronously be changed when a server side event occurs.

## Setup

To use reactive components, you need to add Django Channels and an ASGI capable server to your project and configure WebSocket routing.
You can use e.g. [Daphne](https://github.com/django/daphne)) instead of the standard Django WSGI server:

```bash
uv add channels daphne
```

Add to your Django settings:

```python
#settings.py
INSTALLED_APPS = [
    "tetra", # must be before daphne!
    "daphne", # must be before staticfiles!
    # ... other apps
    "channels",
    "your_app"
]

ASGI_APPLICATION = '<your_project>.asgi.application'
```

Configure your ASGI application:

```python
# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from tetra.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '<your_project>.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

If you don't add a `ProtocolTypeRouter` wrapper, your websockets won't work. However, Tetra automatically detects whether Django Channels is installed and properly configured in your project. When WebSocket support is not available, Tetra logs a warning to your configured logging mechanism, and proceeds without websockets functionality.


## Creating reactive components
To make a component reactive, simply inherit from `ReactiveComponent` instead of `Component`:

```python
from tetra.components import ReactiveComponent, public
from .models import BreakingNews


class NewsTicker(ReactiveComponent):
    headline = public("")
    # this component always subscribes to one channel: "news.updates"
    subscription = "news.updates"

    def load(self, *args, **kwargs) -> None:
        # Fetch the latest news headline from database
        news = BreakingNews.objects.order_by('?').first()
        if news:
            self.headline = news.title
```

## Reactive Models

You can make your Django models reactive by inheriting from `ReactiveModel`. This automatically sends WebSocket notifications when a model instance is saved or deleted.

See [Reactive Models](reactive-models.md) for more information.

## Component Dispatcher

Use `ComponentDispatcher` to push updates from anywhere in your Django application (e.g., in views, tasks, or signals).

```python
from tetra.dispatcher import ComponentDispatcher
from asgiref.sync import async_to_sync

# Async:
await ComponentDispatcher.data_updated("chat.room.general", data={
    "message": "Hello world!"
})

# Sync:
async_to_sync(ComponentDispatcher.data_updated)("chat.room.general", data={
    "message": "Hello world!"
})
```

## Channel subscriptions

Tetra automatically manages WebSocket groups for common scenarios.

When a user connects, they are auto-subscribed to:
- **User group**: `auth.user.{user_id}` (e.g. `auth.user.7`). Reaches all sessions for a specific user.
- **Session group**: `session.{session_key}`. Reaches all tabs in a single browser session.
- **Broadcast group**: `broadcast`. Reaches every connected client. Don't overuse this. It's helpful for global status updates, anonymous news tickers, or system alerts ("Warning! Shutdown planned in 2 minutes.")


### Subscriptions
Define the channel a component should listen to by setting the `subscription` attribute or overriding `get_subscription()`:

```python
class NewsTicker(ReactiveComponent):
    # Fixed subscription
    subscription = "news.updates"
    
    # Or dynamically:
    def get_subscription(self):
        return f"news.{self.category}"
```

### Manual updates and notifications
You can push custom data or trigger events on the client:

#### Updating public properties
```python
await ComponentDispatcher.data_updated("news.updates", data={"headline": "Breaking News!"})
```
This updates the matching public property on all components subscribed to the group.

#### Sending notifications
```python
await ComponentDispatcher.notify("broadcast", "tetra:alert", {"message": "System shutdown in 5m"})
```
This dispatches a custom event on the client that components can listen to using `@public.listen`.

### Adding and removing components

#### Dynamic list updates
When using `ReactiveModel`, Tetra automatically handles list updates via the collection channel. You can also trigger this manually:

```python
# Triggers a component refresh on the parent component (that listens on "demo.todo")
# Each TodoItem listens on "demo.todo.{pk}"
await ComponentDispatcher.component_created("demo.todo", data={"id": 123})
```

#### Removing components
To remove a specific component by its ID:
```python
await ComponentDispatcher.component_removed(group="todos", component_id="tk_1")
```

To remove all components subscribed to a specific *target group* (e.g., removing one ToDo item from a list):
```python
# Notifies "demo.todo" to remove components subscribed to "demo.todo.234"
await ComponentDispatcher.component_removed(
    group="demo.todo",
    target_group="demo.todo.234"
)
```
The *group* is the channel name the message is sent to. You can select the component to delete by *component_id* or *target_group*.


## Channel group naming conventions

Each client *automatically* subscribes to three groups:

* `{app_label}.{model_name}.{user.id}` (e.g. `auth.user.7`)
* `session.{session_key}`
* `broadcast`

You can additionally use you own structure for group channels, but try to be consistent.
Use hierarchical channel group names for better organization:

### Model-specific subgroup
* `auth.user.456.notifications`

### Room/group  
* `chat.room.general`
* `chat.room.developers`
* `chat.room.7825876283765`

### Topic-based
* `news.breaking`
* `news.sports`
* `news.weather`
* `patient.239.file_list`

### Public broadcast
* `system.alerts`


## Performance tips

- **Limit subscriptions**: Only subscribe to channels you actually need
- **Use specific channels**: Avoid creating and sending to broad channels that generate too many events
- **Clean up**: Unsubscribe when components are destroyed

## Debugging

### Django server

You can enable WebSocket specific logging, if you do not already log everything:

```python
# settings.py
LOGGING = {
    'loggers': {
        'tetra.consumers': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

### Client / Browser

Monitor WebSocket connections in browser developer tools (F12) under the Network tab.
