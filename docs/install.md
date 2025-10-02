---
title: Installation
---

# Installation

As a component framework for Django, Tetra requires that you have a Django project setup before installing. [Follow the Django introduction tutorial](https://docs.djangoproject.com/en/4.2/intro/tutorial01/).

Once ready, install Tetra from PyPi:

```
$ pip install tetra
# +reactive components?
# pip install tetra channels daphne
```

If you want to have reactive components as well, you have to install channels and an ASGI capable server like Daphne too. Have a look at [Reactive Components](reactive-components.md) how to get started with them.

!!! warning
    As Tetra is still being developed it has only been tested with Python 3.10-3.12, we intend to support all officially supported Python versions at the time of v1.0.0.

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
    path('tetra/', include('tetra.urls')),
    # Also ensure you have setup static files for development:
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

## Installing esbuild

Tetra requires [esbuild](https://esbuild.github.io), this is used to build your components' JavaScript/CSS into packages, and create sourcemaps so that you can trace errors back to your source Python files. The easiest way to install esbuild is via [Node.js](https://nodejs.org) [npm](https://www.npmjs.com), in the root of your Django project (the directory where `./manage.py` is located):

```
$ npm init  # If you don't already have a npm package.json and ./node_modules directory
$ npm install esbuild
```

By default, Tetra will expect the esbuild binary to be available as `[projectroot]/node_modules/.bin/esbuild`. If you have it installed in a different location you can set `TETRA_ESBUILD_PATH` in your Django `settings.py` file to the correct path.

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

Finally, run the Django development server command as usual. When your files are modified it will rebuild your JS and CSS:

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
/**/static/*/tetra/**
```