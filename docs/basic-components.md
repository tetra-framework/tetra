---
title: Basic Components
---

# Basic Components

`BasicComponent` are simple, reusable building bricks that can be used to stack together interfaces. They support django variables, context, CSS styles, and JavaScript.

**They do *not* support Alpine.js, or any public attributes or methods.** Basic Components should be used for encapsulating reusable components that have no direct client side interaction with component state, and are useful for composing within other components.

As they don't save their state to be resumable, or initiate an Alpine.js component in the browser, they have lower overhead, are rendered faster and use less memory than normal components.

Register them exactly the same way as normal components. Their CSS styles and JavaScript will be bundled with the rest of the library's assets.

Supported features:

- `load` method
- `template`
- `style`
- `script`
- Private methods and attributes

``` python
# yourapp/components/default.py
from tetra import BasicComponent

class MyBasicComponent(BasicComponent):
    # language=html
    template = """
        <div class="card">
            <h2>{{ title }}</h2>
            <button onclick="myUtility()">Click Me</button>
        </div>
    """

    # language=css
    style = """
        .card {
            border: 1px solid #ccc;
            padding: 1rem;
        }
    """

    # language=javascript
    script = """
        function myUtility() {
            console.log('Button clicked!');
            // Can call global Tetra methods or other JavaScript
        }
    """

    def load(self, title="Default Title"):
        self.title = title
```

BasicComponents can include basic JavaScript that will be bundled with your library's assets. 
Unlike full Components, the JavaScript is included as raw code without Alpine.js component registration, 
making it ideal for small utility functions, event handlers, or calling global methods.
```