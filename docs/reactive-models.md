# Reactive Models

Reactive models in Tetra provide a seamless way to synchronize your database changes with the client-side UI in real-time. By inheriting from `ReactiveModel`, your models automatically notify subscribed components whenever an instance is saved, created, or deleted.

!!! info "WebSocket connections are established on-demand"
    WebSocket connections are only established when a page **actually renders** a `ReactiveComponent`. If you have reactive models defined in your codebase but no reactive components are used on a particular page, no WebSocket connection will be initiated.

## Overview

When a `ReactiveModel` is updated on the server:
- A `post_save` signal triggers a notification.
    - If created: `component.created` is sent to the **collection channel** (e.g., "demo.todo").
    - If updated: `component.data_changed` is sent to the **instance channel** (e.g., "demo.todo.236").
- A `post_delete` signal triggers a `component.removed` message to both channels.
- Subscribed Tetra [ReactiveComponents](reactive-components.md) receive these messages and update their UI automatically.

## Usage

To make a model reactive, inherit from `tetra.models.ReactiveModel`. You should also define which fields are safe to be sent to the client in an inner `Tetra` class.

```python
from django.db import models
from tetra.models import ReactiveModel

class TodoItem(ReactiveModel):
    title = models.CharField(max_length=200)
    done = models.BooleanField(default=False)
    secret_note = models.CharField(max_length=200)

    class Tetra:
        # Only these fields will be sent over the WebSocket
        fields = ["title", "done", "model_version"]
```
Note that the *PK* of the model will always be included.

`ReactiveModel`s automatically include a `model_version` field to handle concurrency and deduplication of updates.

### Configuration with the `Tetra` class

The inner `Tetra` class configures the reactive behavior:

*   **`fields`**: A list of field names to be sent to the client on updates. 
    *   For security, it defaults to an empty list (only triggering a `_updateHtml()` on the client).
    *   Use `"__all__"` to send all model fields (use with caution!).
    *   The primary key (`id`) is always included.

## Model Channels

`ReactiveModel` defines two default channels for each instance:

### Instance Channel
Used for updates to a specific record. Default: `{app_label}.{model_name}.{pk}` (e.g., `main.todoitem.1`).
Get it via: `instance.get_tetra_instance_channel()`.

### Collection Channel
Used for notifications about new or deleted records in a collection. Default: `{app_label}.{model_name}` (e.g., `main.todoitem`).
Get it via: `instance.get_tetra_collection_channel()`.

## Subscribing to Models

In your `ReactiveComponent`, you can subscribe to these channels:

### Subscribing to a specific instance
```python
class TodoDetail(ReactiveComponent):
    def load(self, todo):
        self.todo = todo
        self.title = todo.title

    def get_subscription(self):
        return self.todo.get_tetra_instance_channel()
```

### Subscribing to a collection
```python
class TodoList(ReactiveComponent):
    subscription = "main.todoitem"
    
    def load(self):
        self.todos = TodoItem.objects.all()
```
When a new `TodoItem` is created, `TodoList` will automatically call its `_updatHtml()` method on all its clients, which re-render the components from the server.

## Custom Channels

You can override `get_tetra_instance_channel()` or `get_tetra_collection_channel()` on your model to customize the WebSocket group names.

```python
class ProjectTask(ReactiveModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    def get_tetra_instance_channel(self):
        return f"project.{self.project_id}.task.{self.pk}"

    def get_tetra_collection_channel(self):
        return f"project.{self.project_id}.tasks"
```

## Security Considerations

By default, `ReactiveModel` does not send any field data unless explicitly listed in `Tetra.fields`. This prevents accidental exposure of sensitive data like password hashes or private notes.

Always be selective with the fields you include in `Tetra.fields`. If you only need to trigger a re-render of a component without sending data, leave `fields` as an empty list or omit the `Tetra` class entirely.
