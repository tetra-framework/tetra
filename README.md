# Tetra

Full stack component framework for [Django](http://djangoproject.com) using [Alpine.js](https://alpinejs.dev)

Tetra is a new full stack component framework for Django, bridging the gap between your server logic and front end presentation. It uses a public shared state and a resumable server state to enable inplace updates for components. It also encapsulates your Python, HTML, JavaScript and CSS into one file or directory for proximity of related concerns.


## Documentation

Too much for a README. There's a [Documentation](https://tetra.readthedocs.org) page. 

There are also a shortcut to some [examples](https://www.tetraframework.com/examples/).

## Installation

As usual:
```
pip install tetra
```

But wait, this isn't all. Tetra needs some customization in your Django project. 

Read more at [Installation docs](https:/www.tetraframework.com/installation.md)

## Short Overview

For the impatient: here's a short example video that shows what Tetra is capable of:


https://github.com/user-attachments/assets/137c53af-1fc2-48c5-9c53-a007fbad7874



This is done using simple and concise code in one component, rendered in your template with just `{% InfoCard / %}`. No page reload needed.

```python
from tetra import Component, public

class InfoCard(Component):
    title: str = "I'm so excited!"
    content: str = "We got some news for you."
    name: str = public("")

    @public
    def close(self):
        self.client._removeComponent()

    @public
    def done(self):
        print("User clicked on OK, username:", self.name)
        self.content = f"Hi { self.name }! No further news."

    template = """
    <div class="card text-white bg-secondary mb-3" style="max-width: 18rem;">
      <div class="card-header d-flex justify-content-between">
        <h3>Information</h3>
        <button class="btn btn-sm btn-warning" @click="_removeComponent(
        )"><i class="fa fa-x"></i></button>
      </div>
      
      <div class="card-body">
        <h5 class="card-title">{{ title }}</h5>
        <p class="card-text">
          {{ content }}
        </p>
        <p x-show="!name">
          Enter your name below!
        </p>
        <p x-show="name">
            Thanks, {% livevar name %}
        </p>
        <div class="input-group mb-3">

          <input 
            type="text" 
            class="form-control" 
            placeholder="Your name" 
            @keyup.enter="done()"
            x-model="name">
        </div>
        <button 
            class="btn btn-primary" 
            @click="done()" 
            :disabled="name == ''">
            Ok
        </button>
      </div>
      
    </div>
    """
```

## What does Tetra do exactly?

Django on the backend, Alpine.js in the browser
: Tetra combines the power of Django with Alpine.js to make development easier and quicker.

Component encapsulation
: Each component combines its Python, HTML, CSS and JavaScript in one place for proximity of related code.

Resumable server state
: The components' full server state is saved between public method calls. This state is encrypted for security.

Public server methods
: Methods can be made public, allowing you to easily call them from JS on the front end, resuming the component's state.

Shared public state
: Attributes can be decorated to indicate they should be available in the browser as Alpine.js data objects.

Server "watcher" methods
: Public methods can be instructed to watch a public attribute, enabling reactive re-rendering on the server.

Inplace updating from the server
: Server methods can update the rendered component in place. Powered by the Alpine.js morph plugin.

Component library packaging
: Every component belongs to a "library"; their JS & CSS is packed together for quicker browser downloads.

Components with overridable slots
: Components can have multiple {% slot(s) %} which can be overridden when used.

JS/CSS builds using [esbuild](https://esbuild.github.io)
: Both for development (built into runserver) and production your JS & CSS is built with esbuild.

Automatic Js Source Maps
: Source maps are generated during development so that you can track down errors to the original Python files.

Syntax highlighting with type annotations
: Tetra uses type annotations to syntax highlight your JS, CSS & HTML in your Python files with a [VS Code plugin](https://github.com/samwillis/python-inline-source/tree/main/vscode-python-inline-source)

Forms
: `FormComponent`s can act as simple replacements for Django's FormView, but due to Tetra's dynamic nature, a field can e.g. change its value or disappear depending on other fields' values.
