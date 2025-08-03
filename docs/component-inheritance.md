Title: Component Inheritance

# Component inheritance - abstract components

Components basically are inheritable, to create components that bundle common features, which can be reused and extended by more specialized ones. But: **You cannot inherit from already registered components.**

As components are registered automatically by putting them into a library module, you can create *abstract components* to exclude them from registering.

This works with both `BasicComponent` and `Component`.

```python
# no registering here!
class BaseCard(BasicComponent):
    __abstract__ = True
    template = "<div></div>"


# no registering here!
class Card(BaseCard):
    __abstract__ = True
    template: django_html = """
    <div class="card mycard">
      {% slot default %}{% endslot %]}
    </div>
    """


# This component is registered:
class GreenCard(Card):
    style: css = """
    .mycard {
      background-color: green
    }
    """
```

You can even define more than one directory style components in one file, as long as only *one* of them is actually registered, the others must be abstract. 