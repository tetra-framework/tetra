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
- DynamicFormMixin for dynamically updatable FormComponents
- Improve demo site
- Add debug logging handler
- Improved component import error handling
- Allow component names to be dynamic
- `@v` templatetag for "live" rendering of frontend variables
- Better support for Django models
- Experimental FormComponent and ModelFormComponent support with form validation
- Definable extra context per component class
- `reset()` method for FormComponent
- `push_url()` and `replace_url()` component methods

### Changed
- **BREAKING CHANGE**: registering libraries is completely different. Libraries are directories and automatically found. The library automatically is the containing module name now. Explicit "default = Library()" ist disregarded.
- Components should be referenced using PascalCase in templates now
- Components
- Replace **context with __all__ when passing all context in template tags
- More verbose error when template is not enclosed in HTML tags
- Improved component import error handling
- Improved demo site

## [0.1.1] - 2024-04-10
### Changed
- **New package name: tetra**
- Add conditional block check within components
- Update Alpine.js to v3.13.8
- Switch to pyproject.toml based python package
- Improve demo project: TodoList component,- add django-environ for keeping secrets, use whitenoise for staticfiles
- Give users more hints when no components are found
- MkDocs based documentation
- Format codebase with Black

### Added
- Basic testing using pytest

### Fixed
- Correctly find components

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
