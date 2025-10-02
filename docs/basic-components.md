---
title: Basic Components
---

# Basic Components

`BasicComponent` are simple, reusable building bricks that can be used to stack together interfaces. They support django variables, context, and CSS styles. 

**They do *not* support JS, Alpine.js, or any public attributes or methods.** Basic Components should be used for encapsulating reusable components that have no direct client side interaction and are useful for composing within other components.

As they don't save their state to be resumable, or initiate an Alpine.js component in the browser, they have lower overhead, are rendered faster and use less memory than normal components.

Register them exactly the same way as normal components and their CSS styles will be bundled with the rest of the library's styles.

Supported features:

- `load` method
- `template`
- `styles`
- Private methods and attributes

``` python
# yourapp/components/default.py
from tetra import BasicComponent

class MyBasicComponent(BasicComponent):
    ...
```