from tetra import BasicComponent
from sourcetypes import django_html, css

from .base import default


@default.register
class SimpleBasicComponent(BasicComponent):
    template: django_html = "<div id='component'>foo</div>"


@default.register
class SimpleBasicComponentWithCSS(BasicComponent):
    template: django_html = "<div id='component' class='text-red'>bar</div>"
    style: css = ".text-red { color: red; }"


@default.register
class SimpleComponentWithDefaultBlock(BasicComponent):
    template: django_html = (
        "<div id='component'>{% block default %}{% endblock %}</div>"
    )


@default.register
class SimpleComponentWithNamedBlock(BasicComponent):
    template: django_html = "<div id='component'>{% block foo %}{% endblock %}</div>"


@default.register
class SimpleComponentWithNamedBlockWithContent(BasicComponent):
    template: django_html = "<div id='component'>{% block foo %}foo{% endblock %}</div>"


@default.register
class SimpleComponentWithConditionalBlock(BasicComponent):
    template: django_html = """
<div id="component">
{% if blocks.foo %}BEFORE{% block foo %}content{% endblock %}AFTER{% endif %}always
</div>
"""


@default.register
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


@default.register
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


@default.register
class SimpleComponentWith2Blocks(BasicComponent):
    template: django_html = """
<div id="component">{% block default %}default{% endblock %}{% block foo %}foo{% endblock %}</div>
"""


@default.register
class SimpleComponentWithAttrs(BasicComponent):
    template: django_html = """
<div id="component" {% ... attrs class="class1" %}>content</div>
"""
