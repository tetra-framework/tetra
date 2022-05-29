Title: Change Log

# Change Log

> **Note:** Tetra is still early in its development, and we can make no promises about API stability at this stage.
>
> The intention is to stabilise the API prior to a V1 release this summer, as well as  implementing some additional functionality. After V1 we will move to using [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `_parent` client attribute added, this can be used to access the parent component mounted in the client.

- `_redirect` client method added, this can be used to redirect to another url from the public server methods. `self.client._redirect("/test")` would redirect to the `/test` url.

- `_dispatch` client method added, this is a wrapper around the Alpine.js [`dispatch` magic](https://alpinejs.dev/magics/dispatch) allowing you to dispatch events from public server methods. These bubble up the DOM and be captured by listeners on (grand)parent components. Example: `self.client._dispatch("MyEvent", {'some_data': 123})`.

- `_refresh` public method added, this simpley renders the component on the server updating the dom in the browser. This can be used in combination with `_parent` to instruct a parent component to re-render from a child components public method such as: `self.client._parent._refresh()`

### Changed

- Built in Tetra client methods renamed to be prefixed with an underscore so that they are separated from user implemented methods:
    - `updateHtml` is now `_updateHtml`
    - `updateData` is now `_updateData`
    - `removeComponent` is now `_removeComponent`
    - `replaceComponentAndState` is now `_replaceComponent`