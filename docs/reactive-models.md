# Reactive Models

Reactive models in Tetra provide a seamless way to synchronize your database changes with the client-side UI in real-time. By inheriting from `ReactiveModel`, your models automatically notify subscribed components whenever an instance is saved or deleted.

## Overview

When a `ReactiveModel` is updated on the server:
- A `post_save` signal triggers a `component.data_updated` message to the model's WebSocket channel.
- A `post_delete` signal triggers a `component.removed` message.
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
        fields = ["title", "done"]
```

### Configuration with the `Tetra` class

The inner `Tetra` class configures the reactive behavior:

*   **`fields`**: A list of field names to be sent to the client on updates. 
    *   For security, it defaults to an empty list (only triggering a refresh of public properties without sending field data).
    *   Use `"__all__"` to send all model fields (use with caution!).

## Subscribing to Models

In your `ReactiveComponent`, you can subscribe to a specific model instance or a general model channel.

### Subscribing to a specific instance

The default channel for a model instance is `{app_label}.{model_name}.{pk}`.

```python
class TodoDetail(ReactiveComponent):
    todo_id = public()

    def load(self, todo_id):
        self.todo = TodoItem.objects.get(pk=todo_id)
        self.title = self.todo.title

    def get_subscription(self):
        # Subscribe to this specific todo item
        return f"main.todoitem.{self.todo.id}"
```

When the `TodoItem` is saved, `TodoDetail` will automatically receive the updated `title` (if it's in `Tetra.fields`).

### Subscribing in templates

You can also use the `subscribe` argument in the component tag:

```html
{% TodoDetail todo_id=item.id subscribe="main.todoitem."|add:item.id %}
```

## Custom Channels

You can override `get_tetra_channel()` on your model to customize the WebSocket group name. This is useful for filtering updates, for example, by user or project.

```python
class ProjectTask(ReactiveModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

    class Tetra:
        fields = ["title"]

    def get_tetra_channel(self):
        # Notify all components interested in this project
        return f"project.{self.project_id}.tasks"
```

## Security Considerations

By default, `ReactiveModel` does not send any field data unless explicitly listed in `Tetra.fields`. This prevents accidental exposure of sensitive data like password hashes or private notes.

Always be selective with the fields you include in `Tetra.fields`. If you only need to trigger a re-render of a component without sending data, leave `fields` as an empty list or omit the `Tetra` class entirely.
