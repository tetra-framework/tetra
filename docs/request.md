from tetra import Component---
title: Tetra requests
---
# Tetra requests

Tetra requests are modified by `TetraMiddleware`, and spiked with a few helpful attributes.

!!! note
    Make sure you have `tetra.middleware.TetraMiddleware` in your `settings.MIDDLEWARE`

Tetra keeps a track of which components have been used on a page. It then injects the component's CSS and JavaScript into the page. You mark where this is to happen with the `{% tetra_styles %}` and `{% tetra_scripts %}` tags. See [Javascript and JS](include-js-css.md) for details.

## request.tetra

When a component method is called, the request is modified by `TetraMiddleware`. Within the method, a `request.tetra` property is available on the component, providing a set of useful attributes for your application.

#### __bool__()

First, `self.request.tetra` itself evaluates to a bool, indicating whether the current request originated from a Tetra (AJAX) call or not. You can use that for e.g. changing the behavior in your `load()` method:

```python
class MyComponent(Component):
    def load(self):
        if not self.request.tetra:
            # only executes when component is loading the first time, e.g. via browser page reload
        else:
            # this branch is executed only when called from a component method.
```

#### current_url

Within a Tetra component's method call, Django's `request.url` holds the internal *url of the component method*, which is often not what you want: sometimes you want the URL of the whole page. The `request.tetra.current_url` provides the real url of the browser window, so you can parse it. 

```python
>>> self.request.url
'https://example.com/__tetra__/mycomponent/default/foo_method'
>>> self.request.tetra.current_url
'https://example.com/foo/bar'
```

#### current_abs_path

Similarly, you sometimes need the path of the current page. `request.tetra.current_abs_path` holds the cleaned path.

```python
>>> self.request.tetra.current_abs_path
'/foo/bar'
```

#### url_query_params

The same goes for GET parameters. `self.request.GET` means the get params of the Tetra call, which is mostly not what you want.
To receive the GET params of your main URL in the browser, your tetra components can be accessed via `url_query_params`.

E.g. when your page URL is `https://example.com/foo/bar/?tab=main`, within any called component method you can do this:

```python
>>> self.request.tetra.url_query_params.get("tab")
'main'
```

So you can display different things depending on which GET params are given, or keep a certain state (e.g. open tab) when the "tab" param is set.