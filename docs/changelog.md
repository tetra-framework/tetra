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

## [0.8.0] - 2026-01-26
### Changed
- Enhanced middleware efficiency by implementing a fast path for non-Tetra requests, including tests.
- BasicComponents now don't use a Metaclass anymore, but `__init_subclass__()`

## [0.7.3] - 2026-01-25
### Fixed
- Another fix (try?) for file upload vulnerabilities: don't include uploaded file names to form.data when invalid form is rendered. This one is tricky.

## [0.7.2] - 2026-01-20
Fixed: improve file handling security and add tests for file upload vulnerabilities

## [0.7.1] - 2026-01-14
### Added
- Incremental build support for libraries. Tetra now detects changes in component source files (Python, JS, and CSS) and skips `esbuild` if no changes are detected.
- Added `--force` flag to `tetrabuild` management command (via `build` function update) to bypass incremental build check and perform a full rebuild.

### Changed
- Improved `STATIC_ROOT` management during builds: it is now only cleared when `force=True` is used, while individual library directories are still cleaned when they are rebuilt.

## [0.7.0] - 2026-01-13
### Added
- `AppRouter` and `Link` component for dynamic routing/navigation within a container.
- Support for trailing slashes in routes when Django's `APPEND_SLASH` is enabled.
- Support for optional arguments in Router `load` method.
- New routing documentation and comprehensive tests.
- Bundle esbuild within Tetra (auto-download), remove npm dependency.
- rename decorator `@public.subscribe` to `@public.listen` for consistency.

### Fixed
- Memory leak bug when watching files recursively in root directory.
- Ensure all attributes are set when unpickling a component.
- Improved handling of conditional node branches for `{% slot %}` tags.
- Safely patch `Template.compile_nodelist` to preserve the original method.

## [0.6.10] - 2026-01-10
### Added
- Configurable component module names via settings and constants.
- `mypy` added to dev dependencies.
- Tests for importing Tetra without `channels` and `ReactiveComponent` handling.


## [0.6.9] - 2026-01-10
### Fixed
- Ensure Tetra is importable without `channels` when no `ReactiveComponent` is used.
- `npm install` in Makefile.

### Changed
- Use `uv run` for tests in Makefile.
- Use `publish` instead of `publish-prod` in Makefile.

## [0.6.8] - 2026-01-10
### Added
- Loading indicators for buttons now work independently. Each button has its own indicator that only shows while that
  specific button's action is running. When a button finishes its task, only its indicator turns off, while other
  buttons' indicators keep running if their tasks are still in progress.
- Refactored pytest fixtures and test views to be reusable in other packages that use Tetra.

### Fixed
- postpone template compiling to time when all libraries are loaded, so component referrals of not yet loaded components work.

## [0.6.7] - 2026-01-06
### Added
- DownloadButton demo component
- accept dynamic root tags in components (like `<{{ tag }}>) in checks

### Removed
- remove `ViewMixin` from public API - it's not worth all the problems it creates.

## [0.6.6] - 2026-01-05
### Added
- add `ViewMixin` to allow components to be used as standalone Django views with `as_view()`.
- include security-filtered GET parameter retrieval in `ViewMixin`, with automatic injection into `load()`.

### Fixed
-  fix a bug that prevented the `TetraConsumer` from working with channels when DEBUG==False
- 
### Added
- allow "page" components to be used as full Django views

## [0.6.5] - 2026-01-04
## [0.6.3] - 2026-01-04
## [0.6.4] - 2026-01-04
### Changed
- introduced some complicated workarounds for websockets not working properly, introducing a few new bugs... pfff..

## [0.6.2] - 2026-01-04
### Fixed
-  correctly add all js, scripts, staticfiles etc into the pypi package

## [0.6.1] - 2026-01-04
### Fixed
- TetraConsumer now is stricter with allowing user and group subscriptions.

### Added
- Code coverage

## [0.6.0] - 2026-01-02
### Changed
- BREAKING change: rename `tx-indicator` to `t-indicator` HTML class

### Fixed
- build_sh.sh does now produce output code in `src/` directory structure.


## [0.5.3] - 2025-12-20
### Fixed
- fix "optional" channels dependency blocking tetra when not using channels. Only import channels if websockets are needed in project
- components in subdir apps are now found correctly by label

### Changed
- change to a `src/` based directory structure
- Django 6.0 compatibility

### Changed
- switch to playwright in ui component testing

## [0.5.2] - omitted. Don't ask.

## [0.5.1] - 2025-10-03
### Fixed
- use encrypted wss scheme when connecting to server using https
- some smaller bugfixes
### Changed
- clear static files before building libraries 
- get rid of Blacknoise in demo project



## [0.5.0] - 2025-10-02
### Changed
- introduce websocket-enhanced `ReactiveComponent`s

## [0.4.0] - 2025-08-04
### Changed
- rename `request.tetra.current_url_abs_path` to `current_url_full_path` to better adhere to naming standards. `current_url_abs_path` is deprecated.
- **BREAKING CHANGE** remove the `@` tag for component rendering. Use the component name alone.
- **BREAKING CHANGE** disable `{% <app>.<library>.<component_name> /%}` reference. Only allow `{% [<library_name>.]<component_name> / %}`
- **BREAKING CHANGE** rename `@v` tag to `livevar`
- **BREAKING CHANGE** `block` inside components renamed to `slot`
- refactoring of internal Component and Library methods 

### Added
- `request.tetra.current_url_path` that holds the path without query params
- a `tetra` template variable that holds the TetraDetails of a request, or possible equivalents of the current main request.
- Client URL pushes are now anticipated and reflected on the server before rendering the component on updates

## [0.3.1] - 2025-04-19
- **BREAKING CHANGE** rename all `tetra:*` events to kebab-case: `before-request`, `after-request`, `component-updated`, `component-before-remove` etc. This was necessary because camelCase Events cannot be used properly in `x-on:` attributes - HTMX attributes are forced to lowercase, which breaks the event capture.

## [0.3.0] - 2025-04-18
### Added
- beforeRequest, afterRequest events
- add support for loading indicators (=spinners)
- add support for file downloads in component methods

### Changed
- **BREAKING CHANGE** rename all `tetra:*` events to camelCase: `componentUpdated`, `componentBeforeRemove` etc.

### Fixed
- fix file uploads for FormComponent (using multipart/form-data)

## [0.2.1] - 2025-03-29
- fix a small bug that could early-delete temporary uploaded files  

## [0.2.0] - 2025-03-27
### Added
- DynamicFormMixin for dynamically updatable FormComponents
- Improved demo site
- Added debug logging handler
- Improved component import error handling
- Allow component names to be dynamic
- `@v` shortcut templatetag for "live" rendering of frontend variables
- Better support for Django models
- Experimental FormComponent and ModelFormComponent support with form validation
- Definable extra context per component class
- `reset()` method for FormComponent
- `push_url()` and `replace_url()` component methods for manipulating the URL in the address bar
- `recalculate_attrs()` method for calculated updates to attributes before and after component methods
- `request.tetra` helper for *current_url*, *current_abs_path* and *url_query_params*, like in HTMX
- add life cycle Js events when updating/removing etc. components
- add a T-Response header that only is available in Tetra responses.
- Integration of Django messages into Tetra, using T-Messages response header
- `<!-- HTML comments -->` at begin of components are possible now

### Removed
- **BREAKING CHANGE** `ready()` method is removed and functionally replaced with `recalculate_attrs()`

### Changed
- **BREAKING CHANGE**: registering libraries is completely different. Libraries are directories and automatically found. The library automatically is the containing module name now. Explicit "default = Library()" ist disregarded.
- Components should be referenced using PascalCase in templates now
- Component tags: replace `**context` with `__all__` when passing all context in template tags
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
