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
    "channels[types]", # with mypy support!
    "your_app"
]

ASGI_APPLICATION = '<your_project>.asgi.application'

...

CHANNEL_LAYERS = {
    "default": {
        # you can use this in-memory layer for testing,
        # but in production it won't work:
        # "BACKEND": "channels.layers.InMemoryChannelLayer",
        
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
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

If you don't add a `ProtocolTypeRouter` wrapper, your websockets won't work. However, Tetra automatically detects whether Django Channels is installed and properly configured in your project. When WebSocket support is not available, Tetra logs a warning to your configured logging mechanism and proceeds without websockets functionality.


## Creating reactive components
To make a **component** reactive, inherit from `ReactiveComponent` instead of `Component`:

```python
from tetra import ReactiveComponent, public
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

You can then manually send data to the "news.updates" channel, see [Component Dispatcher](#component-dispatcher) below.

## Reactive Models

You can make your Django **models** reactive by inheriting from `ReactiveModel`. This automatically sends WebSocket notifications to predefined channel groups when a model instance is saved, updated, or deleted.

See the [Reactive Models](reactive-models.md) section for more information.

## Online/offline Status

Tetra provides a built-in mechanism to track the online/offline status of the client, which is especially useful for reactive components.

See the [Online Status](online-status.md) section for more information.

## Component Dispatcher

Use `ComponentDispatcher` to push updates from anywhere in your Django application (e.g., in views, tasks, or signals).
The dispatcher is called asynchronously and needs to be wrapped in an async context manager if called from a sync function.

```python
from tetra.dispatcher import ComponentDispatcher
from asgiref.sync import async_to_sync

# Async:
await ComponentDispatcher.data_changed("chat.room.general", data={
    "message": "Hello world!"
})

# Sync:
async_to_sync(ComponentDispatcher.data_changed)("chat.room.general", data={
    "message": "Hello world!"
})
```

Here, all clients that are subsribed to the "chat.room.general" group will receive the updated data 
`{"message": "Hello world!"}`. Tetra automatically tries to match the data format into you component's public properties,
so your receiving component should have a `message` property in this case, which will be updated.

## Channel subscriptions

Tetra automatically manages WebSocket groups for common scenarios.

When a client connects, it is auto-subscribed to:

**User group**: `auth.user.{user_id}` 
: e.g. `auth.user.7`. Reaches all sessions for a specific user. Anonymous users are not subscribed to this group.

**Session group**: `session.{session_key}`
: Reaches all tabs in a single browser session.

**Broadcast group**: `broadcast`
: Reaches every connected client. **Don't overuse it.** It's helpful for global status updates, anonymous news tickers, or system alerts like `"Warning! Shutdown planned in 2 minutes."`



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
await ComponentDispatcher.data_changed("news.updates", data={"headline": "Breaking News!"})
```
This updates the matching public property on all components subscribed to the group.

#### Sending notifications
```python
await ComponentDispatcher.notify(
    group="broadcast", 
    event_name="tetra:alert", 
    data={"message": "System shutdown in 5m"}
)
```
This dispatches a custom JavaScript event on the client that components can listen to using `@public.listen`.

### Adding and removing components

#### Dynamic list updates
When using `ReactiveModel`, Tetra automatically handles list updates via the collection channel. But you can also trigger this manually:

```python
# Triggers a component refresh on the parent component (that listens on "demo.todo")
# Each TodoItem listens on "demo.todo.{pk}"
await ComponentDispatcher.component_created("demo.todo", data={"pk": 123})
```

#### Removing components
To remove a specific component by its `component_id`:
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

You can additionally use your own structure for group channels but try to be consistent. Use hierarchical channel group names for better organization:

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
- **Avoid circle event storms**: Don't save models in components that trigger updates on components that trigger updates on models that... You get the point.

Tetra does its best to avoid:
- **unnecessary updates**: you have fine-grained control over which components receive updates by subscribing to specific channels, and much more. 
- **message echoing**: websocket messages sent to the same client where the originating request came from, targeting the originating component, are ignored

Nevertheless, Tetra is not a silver bullet. So choose your architecture wisely.

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

Monitor WebSocket connections/messages in browser developer tools (F12) under the Network tab.
