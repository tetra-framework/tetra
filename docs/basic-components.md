---
title: Basic Components
---

# Basic Components

`BasicComponent` supports CSS, but not JS, Alpine.js, or any public attributes or methods. Basic Components should be used for encapsulating reusable components that have no direct client side interaction and are useful for composing within other components.

As they don't save their state to be resumable, or initiate an Alpine.js component in the browser, they have lower overhead.

They are registered exactly the same way as normal components and their CSS styles will be bundled with the rest of the library's styles.

Supported features:

- `load` method
- `template`
- `styles`
- Private methods and attributes

``` python
from tetra import BasicComponent

class MyBasicComponent(BasicComponent):
    ...
```