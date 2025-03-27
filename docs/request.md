---
title: Tetra requests
---
# Tetra requests

Tetra requests are modified by `TetraMiddleware`, and spiked with a few helpful attributes.

!!! note
    Make sure you have `tetra.middleware.TetraMiddleware` in your `settings.MIDDLEWARE`

Tetra keeps a track of which components have been used on a page. It then injects the component's CSS and JavaScript into the page. You mark where this is to happen with the `{% tetra_styles %}` and `{% tetra_scripts %}` tags. See [Javascript and JS](include-js-css.md) for details.

## request.tetra

When a component method is called, the request is modified by `TetraMiddleware`. Within the method, a `request.tetra` property is available on the component, providing a set of useful attributes for your application:

#### current_url

Within a Tetra component's method call, Django's `request.url` holds the internal *url of the component method*, which is often not what you want: sometimes you want the URL of the whole page. The `request.tetra.current_url` provides the real url of the browser window, so you can parse it. 

```python
>>> self.request.tetra.current_url
>>> 'https://example.com/foo/bar'
```

#### current_abs_path

Similarly, you sometimes need the path of the current page. `request.tetra.current_abs_path` holds the cleaned path.

```python
>>> self.request.tetra.current_abs_path
>>> '/foo/bar'
```

#### url_query_params

When you pass GET params to your main URL in the browser, your tetra components can access these via `url_query_params`.

E.g. when your page URL is `https://example.com/foo/bar/?tab=main`

```python
>>> self.request.tetra.url_query_params.get("tab")
>>> 'main'
```

So you can e.g. display different things depending on which GET params are given, or keep a certain state (e.g. open tab) when the "tab" param is set.