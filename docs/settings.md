---
title: Settings
---

# Settings

Tetra exposes some Django settings variables, you can change them to your needs.


## `TETRA_TEMP_UPLOAD_PATH`

You can manually set the directory where FormComponent saves its temporary file upload (relative to MEDIA_ROOT). The standard is `tetra_temp_upload`.

```python
TETRA_TEMP_UPLOAD_PATH = "please_pass_by_nothing_to_see_here"
```


## `TETRA_FILE_CACHE_DIR_NAME`

How Tetra names its cache directories. Normally you shouldn't change this. Defaults to `__tetracache__`.


## `TETRA_COMPONENTS_MODULE_NAMES`

A list of module names that contain components in your apps.

Defaults to `["components", "tetra_components"]`


## `TETRA_ESBUILD_PATH`

The path to the `esbuild` binary. By default, Tetra will try to find `esbuild` in your `PATH`. If you have installed `esbuild` via `npm` in your project root, you can set this to `os.path.join(BASE_DIR, "node_modules", ".bin", "esbuild")`.


## `TETRA_ESBUILD_CSS_ARGS` and `TETRA_ESBUILD_JS_ARGS`

These are used to pass additional arguments to the `esbuild` process for CSS and JS respectively. They should be lists of strings. Default is `[]`.