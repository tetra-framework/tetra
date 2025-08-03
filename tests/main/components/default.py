from tetra import BasicComponent, public, Component
from sourcetypes import django_html, css


class SimpleBasicComponent(BasicComponent):
    template: django_html = "<div id='component'>foo</div>"


class SimpleBasicComponentWithCSS(BasicComponent):
    template: django_html = "<div id='component' class='text-red'>bar</div>"
    style: css = ".text-red { color: red; }"


class SimpleComponentWithDefaultBlock(BasicComponent):
    template: django_html = "<div id='component'>{% slot default %}{% endslot %}</div>"


class SimpleComponentWithNamedBlock(BasicComponent):
    template: django_html = "<div id='component'>{% slot foo %}{% endslot %}</div>"


class SimpleComponentWithNamedBlockWithContent(BasicComponent):
    template: django_html = "<div id='component'>{% slot foo %}foo{% endslot %}</div>"


class SimpleComponentWithConditionalBlock(BasicComponent):
    template: django_html = (
        """<div id="component">{% if slots.foo %}BEFORE{% slot foo %}content{% endslot %}AFTER{% endif %}always</div>"""
    )


class SimpleComponentWithConditionalBlockAndAdditionalContent(BasicComponent):
    template: django_html = (
        """<div id="component">BE{% if slots.foo %}FORE{% slot foo %}{% endslot %}AF{% endif %}TER</div>"""
    )


class SimpleComponentWithConditionalBlockAndAdditionalHtmlContent(BasicComponent):
    template: django_html = """
<div id="component"><div>
{% if slots.foo %}
<span>{% slot foo %}{% endslot %}</span>
{% endif %}
</div></div>
"""


class SimpleComponentWith2Blocks(BasicComponent):
    template: django_html = """
<div id="component">{% slot default %}default{% endslot %}{% slot foo %}foo{% endslot %}</div>
"""


class SimpleComponentWithAttrs(BasicComponent):
    template: django_html = """
<div id="component" {% ... attrs class="class1" %}>content</div>
"""


class SimpleComponentWithFooContext(BasicComponent):
    """Simple component that adds "foo" context"""

    _extra_context = ["foo"]
    template: django_html = """
    <div id="component">{% slot default %}{% endslot %}</div>
    """


class SimpleComponentWithExtraContextAll(BasicComponent):
    """Simple component that adds __all__ global context"""

    _extra_context = ["__all__"]
    template: django_html = """
    <div id="component">{% slot default %}{% endslot %}</div>
    """


# --------------------------------------------------


class SimpleComponentWithAttributeInt(BasicComponent):
    my_int: int = 23
    template: django_html = "<div id='component'>int: {{ my_int }}</div>"


class SimpleComponentWithAttributeFloat(BasicComponent):
    my_float: float = 2.32
    template: django_html = "<div id='component'>float: {{ my_float }}</div>"


class SimpleComponentWithAttributeList(BasicComponent):
    my_list: list = [1, 2, 3]
    template: django_html = "<div id='component'>list: {{ my_list }}</div>"


class SimpleComponentWithAttributeDict(BasicComponent):
    my_dict: dict = {"key": "value"}
    template: django_html = "<div id='component'>dict: {{ my_dict }}</div>"


class SimpleComponentWithAttributeSet(BasicComponent):
    my_set: set = {1, 2, 3}
    template: django_html = "<div id='component'>set: {{ my_set }}</div>"


class SimpleComponentWithAttributeFrozenSet(BasicComponent):
    my_set: frozenset = frozenset({1, 2, 3})
    template: django_html = "<div id='component'>frozenset: {{ my_set }}</div>"


class SimpleComponentWithAttributeBool(BasicComponent):
    my_bool: bool = False
    template: django_html = "<div id='component'>bool: {{ my_bool }}</div>"


class ComponentWithPublic(Component):
    msg = public("Message")

    @public
    def do_something(self) -> str:
        pass

    template: django_html = "<div id='component'>{{ message }}</div>"
