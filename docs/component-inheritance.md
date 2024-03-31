Title: Component Inheritance

# Component Inheritance

Components are inheritable, to create components that bundle common features, which can be reused and extended by more
specialized ones.

The only thing you have to conform to is: **You cannot inherit from already registered components.**
So create a "base" component without registering it, and just register the inherited components.

This works with both `BasicComponent` and `Component`.

``` python
# no registering here!
class CardBase(BasicComponent):
    template: django_html = """
    <div class="card mycard">
      ...
    </div>
    """

# now register the components
@default.register
class Card(CardBase):
    template: django_html = """
    <div class="card">
      {% block default %]{% endblock %]}
    </div>
    """

@default.register
class GreenCard(CardBase):
    style: css = """
    .mycard {
      background-color: green
    }
    """
```