---
title: Changelog
---

# Changelog

!!! note
    Tetra is still early in its development, and we can make no promises about
    API stability at this stage.

    The intention is to stabilise the API prior to a v1.0 release, as well as
    implementing some additional functionality.
    After v1.0 we will move to using [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - unreleased
### Added
- improve demo site
- add debug logging handler
- improved component import error handling
- allow component names to be dynamic
- @v templatetag for "live" rendering of frontend variables
- support Django models in TetraJSONEn/Decoder
- experimental FormComponent and GenericObjectFormComponent support with form validation

## [0.1.1] - 2024-04-10
### Changes
- **New package name: tetra**
- add conditional block check within components
- Update Alpine.js to v3.13.8
- switch to pyproject.toml based python package
- improve demo project: TodoList component,- add django-environ for keeping secrets, use whitenoise for staticfiles
- give users more hints when no components are found
- MkDocs based documentation
- format codebase with Black

### Added
- basic testing using pytest

### Fixed
- correctly find components

## [0.0.5] - 2022-06-13
### Changed
- **This is the last package with the name "tetraframework", transition to "tetra"**
- Provisional Python 3.8 support

### Fixed
- Windows support


## [0.0.4] - 2022-06-22
- Cleanup


## [0.0.3] - 2022-05-29
### Added
- `_parent` client attribute added, this can be used to access the parent component mounted in the client.
- `_redirect` client method added, this can be used to redirect to another url from the public server methods. `self.client._redirect("/test")` would redirect to the `/test` url.
- `_dispatch` client method added, this is a wrapper around the Alpine.js [`dispatch` magic](https://alpinejs.dev/magics/dispatch) allowing you to dispatch events from public server methods. These bubble up the DOM and be captured by listeners on (grand)parent components. Example: `self.client._dispatch("MyEvent", {'some_data': 123})`.
- `_refresh` public method added, this simply renders the component on the server updating the dom in the browser. This can be used in combination with `_parent` to instruct a parent component to re-render from a child components public method such as: `self.client._parent._refresh()`

### Changed
- Built in Tetra client methods renamed to be prefixed with an underscore so that they are separated from user implemented methods:
    - `updateHtml` is now `_updateHtml`
    - `updateData` is now `_updateData`
    - `removeComponent` is now `_removeComponent`
    - `replaceComponentAndState` is now `_replaceComponent`