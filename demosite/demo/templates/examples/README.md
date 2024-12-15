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

* The `text.md` file contains the description of the example, with code sections. This is rendered as HTML. It must contain a `title` as front matter. You can include source files using `{% md_include_source 'path/to/file' 'optional_first_line_comment' %}`
* The `demo.html` part, which is a django template, using the Tetra component, is rendered.
