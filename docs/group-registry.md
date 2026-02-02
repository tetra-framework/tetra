### WebSocket Group Registry

Tetra uses a "deny-by-default" strategy for WebSocket group subscriptions to enhance security. This prevents clients from guessing and subscribing to sensitive internal groups.

Only groups that are explicitly registered in the `group_registry` can be manually subscribed to from the client side.

#### Automatic Registration

##### Reactive Models
`ReactiveModel` automatically registers its collection group and an instance group pattern upon initialization. 

For a model named `MyModel` in an app called `myapp`:
*   `myapp.mymodel`: The collection group (e.g., for `component_created` events).
*   `myapp.mymodel.*`: A regex pattern matching any instance of that model (e.g., `myapp.mymodel.123`).

This ensures that reactive components can subscribe to these groups without any manual configuration from the developer.

#### Automated Groups (Exempt from Registry)

Certain groups follow an automated scheme and do not require registration in the `group_registry`. The `TetraConsumer` handles these with specific logic, and auto-joins clients to them upon connection. **Manual subscription to these groups is explicitly blocked** for security and to maintain their automated behavior:

*   **`broadcast`**: Public group for *any client*
*   **`users`**: All *authenticated users*
*   **`session.{session_key}`**: The current session of the user (e.g., one or more browser tabs)
*   **`{user_prefix}.{user_id}`**: (e.g., `auth.user.1`) The private user group for one user

#### Manual Registration

If you need to use custom groups for your application (e.g., a chat room or a specific notification channel), you must register them in the `group_registry` before a client can subscribe to them. A good place to do this is in your `AppConfig.ready()` method.

You can register exact group names or regex patterns.

##### Registering an Exact Group Name

```python
from tetra.registry import channels_group_registry

channels_group_registry.register("chatroom.lobby")
```

##### Registering a Pattern

```python
import re
from tetra.registry import channels_group_registry

# Allows any group starting with "chatroom."
channels_group_registry.register(re.compile(r"^chatroom\..+$"))
```

#### Subscription Errors

If a client attempts to subscribe to a group that is not registered (and not one of the exempted automated groups), the subscription will be denied.

*   **Server-side**: A warning will be logged: `Subscription to unregistered group 'group_name' blocked.`
*   **Client-side**: The subscription request will return an error status with the message `"Subscription group is not registered"`.
