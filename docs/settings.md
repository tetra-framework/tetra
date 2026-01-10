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


## others

`TETRA_ESBUILD_CSS_ARGS` and `TETRA_ESBUILD_JS_ARGS` are used internally. Please look at the code if you really want to change these.