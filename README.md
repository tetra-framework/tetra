# Tetra

Full stack component framework for [Django](http://djangoproject.com) using [Alpine.js](https://alpinejs.dev)

Tetra is a new full stack component framework for Django, bridging the gap between your server logic and front end presentation. It uses a public shared state and a resumable server state to enable inplace updates. It also encapsulates your Python, HTML, JavaScript and CSS into one file for close proximity of related concerns.

See  examples at [tetraframework.com](https://www.tetraframework.com)

Read the [Documentation](https://www.tetraframework.com/docs)

```
pip install tetraframework
```

## What does Tetra do?

  - Django on the backend, Alpine.js in the browser

    Tetra combines the power of Django with Alpine.js to make development easier and quicker.

  - Component encapsulation

    Each component combines its Python, HTML, CSS and JavaScript in one place for close proximity of related code.

  - Resumable server state

    The components' full server state is saved between public method calls. This state is encrypted for security.

  - Public server methods

    Methods can be made public, allowing you to easily call them from JS on the front end, resuming the component's state.

  - Shared public state

    Attributes can be decorated to indicate they should be available in the browser as Alpine.js data objects.

  - Server "watcher" methods

    Public methods can be instructed to watch a public attribute, enabling reactive re-rendering on the server.

  - Inplace updating from the server

    Server methods can update the rendered component in place. Powered by the Alpine.js morph plugin.

  - Component library packaging

    Every component belongs to a "library"; their JS & CSS is packed together for quicker browser downloads.

  - Components with overridable blocks

    Component can have multiple {% block(s) %} which can be overridden when used.

  - JS/CSS builds using [esbuild](https://esbuild.github.io)

    Both for development (built into runserver) and production your JS & CSS is built with esbuild.

  - Source Maps

    Source maps are generated during development so that you can track down errors to the original Python files.

  - Syntax highlighting with type annotations

    Tetra uses type annotations to syntax highlight your JS, CSS & HTML in your Python files with a [VS Code plugin](https://github.com/samwillis/python-inline-source/tree/main/vscode-python-inline-source)