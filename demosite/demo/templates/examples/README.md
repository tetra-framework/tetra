# Examples

This directory contains Tetra examples. It follows a certain structure:

```
name_of_example/
  demo.html
  text.md
  component.py
other_example/
  demo.html
  text.md
  component.py
```

* The `text.md` file contains the description of the example, with code sections. This is rendered ad HTML. It must contain a `title` as front matter. 
* The `demo.html` part, which is a django template, using the Tetra component, is rendered.
* The `component` itself is located in `demo/components/examples` as `Library()` named "examples". 