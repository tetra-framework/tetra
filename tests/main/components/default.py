from tetra import BasicComponent
from sourcetypes import django_html, css


class SimpleBasicComponent(BasicComponent):
    template: django_html = "<div id='component'>foo</div>"


class SimpleBasicComponentWithCSS(BasicComponent):
    template: django_html = "<div id='component' class='text-red'>bar</div>"
    style: css = ".text-red { color: red; }"


class SimpleComponentWithDefaultBlock(BasicComponent):
    template: django_html = (
        "<div id='component'>{% block default %}{% endblock %}</div>"
    )


class SimpleComponentWithNamedBlock(BasicComponent):
    template: django_html = "<div id='component'>{% block foo %}{% endblock %}</div>"


class SimpleComponentWithNamedBlockWithContent(BasicComponent):
    template: django_html = "<div id='component'>{% block foo %}foo{% endblock %}</div>"


class SimpleComponentWithConditionalBlock(BasicComponent):
    template: django_html = """
<div id="component">
{% if blocks.foo %}BEFORE{% block foo %}content{% endblock %}AFTER{% endif %}always
</div>
"""


class SimpleComponentWithConditionalBlockAndAdditionalContent(BasicComponent):
    template: django_html = """
<div id="component">
BE
{% if blocks.foo %}
FORE
{% block foo %}{% endblock %}
AF
{% endif %}
TER
</div>
"""


class SimpleComponentWithConditionalBlockAndAdditionalHtmlContent(BasicComponent):
    template: django_html = """
<div id="component">
<div>
{% if blocks.foo %}
<span>
{% block foo %}{% endblock %}
</span>
{% endif %}
</div>
</div>
"""


class SimpleComponentWith2Blocks(BasicComponent):
    template: django_html = """
<div id="component">{% block default %}default{% endblock %}{% block foo %}foo{% endblock %}</div>
"""


class SimpleComponentWithAttrs(BasicComponent):
    template: django_html = """
<div id="component" {% ... attrs class="class1" %}>content</div>
"""


class SimpleComponentWithFooContext(BasicComponent):
    """Simple component that adds "foo" context"""

    _extra_context = ["foo"]
    template: django_html = """
    <div id="component">{% block default %}{% endblock %}</div>
    """


class SimpleComponentWithExtraContextAll(BasicComponent):
    """Simple component that adds __all__ global context"""

    _extra_context = ["__all__"]
    template: django_html = """
    <div id="component">{% block default %}{% endblock %}</div>
    """


# --------------------------------------------------


class SimpleComponentWithAttributeStr(BasicComponent):
    foo: str = ""
    template: django_html = "<div id='component'>str: {{ foo }}</div>"
