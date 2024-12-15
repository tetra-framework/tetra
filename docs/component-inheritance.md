Title: Component Inheritance

# Component Inheritance

Components basically are inheritable, to create components that bundle common features, which can be reused and extended by more specialized ones. But: **You cannot inherit from already registered components.**

As components are registered automatically by putting them into a library module, you can create *abstract components* to exclude them from registering.

This works with both `BasicComponent` and `Component`.

``` python
# no registering here!
class CardBase(BasicComponent):

    __abstract__ = True

    template = "<div></div>"

class Card(CardBase):
    
    __abstract__ = True

    template: django_html = """
    <div class="card mycard">
      {% block default %}{% endblock %]}
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