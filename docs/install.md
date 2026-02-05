---
title: Installation
---

# Installation

As a component framework for Django, Tetra requires that you have a Django project setup before installing. [Follow the Django introduction tutorial](https://docs.djangoproject.com/en/4.2/intro/tutorial01/).

Once ready, install Tetra from PyPi - we recommend to use [uv](https://docs.astral.sh/uv/) as package manager:

```
$ uv pip install tetra
```

### For reactive components

If you want to have reactive components as well, you need to install channels, channels-redis, and an ASGI capable server like Daphne:

```bash
$ uv add channels channels-redis daphne
```

You will also need a Redis server running. Install Redis using your system's package manager or [from redis.io](https://redis.io/download).

!!! warning
    As Tetra is still being developed it has only been tested with Python 3.12-3.13, we intend to support all officially supported Python versions at the time of v1.0.0.

## Initial configuration

Modify your Django `settings.py`:

* Add `tetra` to your INSTALLED_APPS (if you use `daphne` or `django.contrib.staticfiles`, put tetra *before* daphne!)
* add `tetra.middleware.TetraMiddleware` to your middlewares

``` python
INSTALLED_APPS = [
    ...
    # Add the tetra app!
    # Tetra must be before the Django staticfiles app (and daphne, if you use it) 
    # in INSTALLED_APPS so that the Tetra's 'runserver' command takes precedence as it will 
    # automatically recompile your JS & CSS during development.
    "tetra",
    # "daphne",
    ...
    "django.contrib.staticfiles",
    ...
]

MIDDLEWARE = [
    ...
    # Add the Tetra middleware at the end of the list.
    # This adds the JS and CSS for your components to HTML responses
    "tetra.middleware.TetraMiddleware"
]
```

### Channels configuration for reactive components

If you are planning to use reactive components, add the following to your `settings.py`:

```python
INSTALLED_APPS = [
    "tetra",  # must be before daphne!
    "daphne",  # must be before staticfiles!
    # ... other apps
    "channels",
    # ... your apps
]

ASGI_APPLICATION = '<your_project>.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env.str("REDIS_HOST", default=("127.0.0.1", 6379))],
        },
    },
}
```

!!! note
    The example above uses `env.str()` from [django-environ](https://django-environ.readthedocs.io/) to read the Redis host from environment variables. 
    You can also hardcode it as `"hosts": [("127.0.0.1", 6379)]` or use your preferred configuration method.

Configure your ASGI application in `asgi.py`:

```python
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

For more details on reactive components, see [Reactive Components](reactive-components.md).

Modify your `urls.py`:

``` python
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    ...
    # Add the Tetra app urls:
    # These include the endpoints that your components will connect to when 
    # calling public methods.
    path('__tetra__/', include('tetra.urls')),
    # Also ensure you have setup static files for development:
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

## Installing esbuild

Tetra requires [esbuild](https://esbuild.github.io), this is used to build your components' JavaScript/CSS into packages, and create sourcemaps so that you can trace errors back to your source Python files.

Tetra comes bundled with esbuild binaries for the most common platforms (Linux, macOS and Windows on x64 and ARM64). It will automatically detect your platform and use the bundled binary.

If you are on an unsupported platform, or want to use a different version of esbuild, you can install it manually (e.g. via `npm install esbuild`) and set `TETRA_ESBUILD_PATH` in your Django `settings.py` file to the correct path.

## Modify base template

Next, ensure that you have included the `tetra_styles` and `tetra_scripts` tags in your base HTML template. These instruct the `TetraMiddleware` where to insert the CSS and JavaScript for the components used on the page:

``` django
{% load tetra %}
<html>
  <head>
    ...
    {% tetra_styles %}
    {% tetra_scripts include_alpine=True %}
  </head>
  ...
```

## Inline syntax highlighting

If you are using [VS Code](https://code.visualstudio.com) you can use the [Python Inline Source](https://marketplace.visualstudio.com/items?itemName=samwillis.python-inline-source) extension to syntax highlight the inline HTML, CSS and JavaScript in your component files. It looks for Python type annotations labeling the language used in strings.

## Running the dev server

Finally, run the Django development server command as usual. When your files are modified, it will rebuild your JS and CSS:

```
$ python manage.py runserver
```

You can also manually run the component build process with:

```
$ python manage.py tetrabuild
```

## .gitignore

While you might want to use a common [Django .gitignore file like from gitignore.io](https://www.toptal.com/developers/gitignore/api/django), you should add this to not accidentally check in cache files into your VCS:

```
# Tetra
__tetracache__/
**/static/*/tetra/**
```