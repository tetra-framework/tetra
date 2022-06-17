# Tetra

Full stack component framework for [Django](http://djangoproject.com) using [Alpine.js](https://alpinejs.dev)

**Tetra is a new Django full stack component framework that bridges the gap between your server logic and front end presentation.
To enable in-place updates, it employs a public shared state and a resumable server state.
It also combines your Python, HTML, JavaScript, and CSS into a single file for easy access to related concerns.**

See  examples at [tetraframework.com](https://www.tetraframework.com)

Read the [Documentation](https://www.tetraframework.com/docs)

```
pip install tetraframework
```

## What does Tetra do?

  - Django on the backend, Alpine.js in the browser

    Tetra combines Django's power with Alpine.js to make development easier and faster.


  - Encapsulation of components

    Each component combines its Python, HTML, CSS, and JavaScript code in one location for easy access to related code.


  - Resumable server state

    Between public method calls, the components' full server state is saved. For security, this state is encrypted.

  - Public server methods

    Methods can be made public, allowing you to easily call them from JS on the front end, resuming the state of the component's.


  - Shared public state

    Attributes can be decorated to indicate that they should be available as Alpine.js data objects in the browser.


  - Server "watcher" methods

    Public methods can be instructed to watch a public attribute, enabling reactive re-rendering on the server.

  - Inplace updating from the server

    Server methods can update the rendered component in place. Powered by the Alpine.js morph plugin.

  - Component library packaging

    Every component is part of a "library," and their JS and CSS are combined for faster browser downloads. 

  - Components with overridable blocks

    Component can have multiple {% block(s) %} which can be overridden when used.

  - JS/CSS builds using [esbuild](https://esbuild.github.io)

    Both for development (built into runserver) and production your JS & CSS is built with esbuild.

  - Source Maps

    Source maps are generated during development so that you can track down errors to the original Python files.

  - Syntax highlighting with type annotations

    Tetra uses type annotations to syntax highlight your JS, CSS & HTML in your Python files with a [VS Code plugin](https://github.com/samwillis/python-inline-source/tree/main/vscode-python-inline-source)