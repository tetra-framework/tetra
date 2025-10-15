---
title: Reactive components
---
# Reactive components

Tetra optionally features async, bidirectional communication using Django channels/websockets. You can use that in "Reactive components" that maintain a long-lasting HTTP connection to the server.

Reactive components can (as the name may suggest) *react* to events that are triggered on the server. This way, a component displayed on multiple clients can synchronously be changed when a server side event occurs.

## Setup

To use reactive components, you need to install Django Channels and configure WebSocket routing. You have to use an ASGI capable server (e.g. [Daphne](https://github.com/django/daphne)) instead of the standard Django WSGI server:

```bash
pip install channels daphne
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

ASGI_APPLICATION = 'your_project.asgi.application'
```

Configure your ASGI application:

```python
# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from tetra.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

```

## Creating reactive components
To make a component reactive, simply inherit from `ReactiveComponent` instead of `Component`:

```python
import random
from tetra.components import ReactiveComponent, public
from .models import BreakingNews


class NewsTicker(ReactiveComponent):
    breaking_news: list = []
    group_subscription = "news.updates"  # this component always subscribes to one channel

    def load(self, *args, **kwargs) -> None:
        # Fetch the latest news headline from database
        self.breaking_news = BreakingNews.objects.all()
        # get random item from BreakingNews
        self.headline = random.choice(self.breaking_news).title    
```


## Channel subscriptions

Tetra keeps track of each `ReactiveComponent` that subscribed to a channel group. When sending push notifications to a group, you can refer to that component by its `component_id` again.

A `ReactiveComponent` that is rendered one a page in the context of an authenticated user with the id 7 has joined the groups `user.7`, `session.jyox98seevk9dll9fy8cyb7wspdnyala` and `broadcast`.

These groups can be used to dispatch component notifications to 

* **one specific user**: No matter where he/she is connected, all sessions on all devices are reached. This is especially useful for user messages, list updates etc.
* **one session**: This is just for one website user (even not authenticated), *at one device, but maybe multiple opened tabs*. Useful for updates that should not be visible on other devices, like unsaved data in a form.
* **everyone**: the `broadcast` group reaches ALL connected devices. Don't overuse this. It's helpful for global status updates, anonymous new tickers, or system alerts ("Warning! Shutdown planned in 2 minutes.")

You can manually add other subscriptions, with three flavours:

### Static subscriptions

Define channels to subscribe to using the `subscribe` attribute:

```python
class NewsTicker(ReactiveComponent):
    group_subscription = "news.headline"
```

These component, when initialized at the client, subscribes via websockets to the given channel and listen to it from then on.

### Dynamic subscriptions

Subscribe and unsubscribe programmatically:

```python
class DynamicChatComponent(ReactiveComponent):
    _current_room_name = "general"

    @public
    def current_room(self):
        return self._current_room_name

    @public
    def change_room(self, room_name):
        # stop listening to messages in old room
        self.client._unsubscribe(f"chat.room.{self._current_room_name}")

        # Subscribe to new room
        self._current_room_name = room_name
        self.client._subscribe(f"chat.room.{room_name}")
```

### Template subscriptions

You can also specify subscriptions directly in templates:

```django
{% ChatComponent subscribe="chat.room.general" %}
```

The subscribed group can of course be a variable, too:

```django
{% ChatComponent subscribe=person.room %}
```


## Sending data to clients

Generally, websocket data are sent asynchronously. Tetra provides a `ComponentDispatcher` class to simplify that often used task.
It provides methods for component data updates, notifications, component removal requests, etc.


Use `ComponentDispatcher`'s utility functions to push messages from anywhere in your Django app:

```python
from tetra.dispatcher import ComponentDispatcher
from asgiref.sync import async_to_sync

# async:
async def send_message():
    # update the public data of any component
    await ComponentDispatcher.update_data("chat.room.hprc", data={
        "message": "Hello Mat, this is Fred Wesley! I'd like to reconfirm our appointment in Munich tomorrow. We'll see us at the hotel."
    })

# or sync:
def send_message():
    # update the public data of any component
    async_to_sync(ComponentDispatcher.update_data)("chat.room.hprc",
        data={
            "message": "..."
        })
```

!!! Important!
    Make absolutely sure that the data you are sending is a dict with keys that match your target components' public properties. They will be updated with that data on the client.

The `ComponentDispatcher` does NOT change the server state of the components.
You have two ways of saving the sent data permanently:

* Save the data on the server, then send it to the client. This is normally done for model "changed" signals: after a model change, send the data out to all clients.
* When the data is meant to be transient, just send it to the client and let it decide if it wants to save it again using the normal Tetra component methods.


## Channel group naming conventions

Each component *automatically* subscribes to three groups:

* `user.{user.id}`
* `session.{session_key}`
* `broadcast`

Additionally, use hierarchical channel group names for better organization:

### User-specific
* `user.456.notifications`

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
- **Use specific channels**: Avoid broad channels that generate too many events  
- **Clean up**: Unsubscribe when components are destroyed

## Debugging

### Django server

Enable WebSocket logging:

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
