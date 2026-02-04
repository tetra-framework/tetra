import pytest
from tetra.utils import has_single_root


def test_simple_single_root():
    assert has_single_root("<div></div>") is True
    assert has_single_root("  <div class='test'><span>content</span></div>  ") is True


def test_multiple_roots():
    assert has_single_root("<div></div><div></div>") is False
    assert has_single_root("<div></div>Text") is False
    assert has_single_root("Text<div></div>") is False


def test_django_tags():
    assert has_single_root("{% if true %}<div></div>{% endif %}") is True
    assert has_single_root("<div>{% if true %}<span></span>{% endif %}</div>") is True
    assert has_single_root("{% block content %}<div></div>{% endblock %}") is True


def test_django_comments():
    assert has_single_root("{# comment #}<div></div>") is True
    assert has_single_root("<div>{# comment #}</div>") is True


def test_django_variables_as_tags():
    assert has_single_root("<{{ tag }}>content</{{ tag }}>") is True
    assert has_single_root("<{{ tag }} class='test'>content</{{ tag }}>") is True


def test_django_variables_in_content():
    assert has_single_root("<div>{{ variable }}</div>") is True
    assert has_single_root("<div {{ attr }}='val'></div>") is True


def test_no_tags():
    assert has_single_root("") is False
    assert has_single_root("   ") is False
    assert has_single_root("just text") is False


def test_complex_dynamic_tag():
    template = """
    <{{ tag }} class="..."{% if tag == "form" %} method="post" action="."{% endif %}>
    ...
    </{{ tag }}>
    """
    assert has_single_root(template) is True


def test_nested_with_django_logic():
    template = """
    <div>
        {% for item in items %}
            <span>{{ item }}</span>
        {% endfor %}
    </div>
    """
    assert has_single_root(template) is True


def test_html_comments():
    assert has_single_root("<!-- comment --><div></div>") is True
    assert has_single_root("<div></div><!-- comment -->") is True
    assert has_single_root("<div><!-- comment --></div>") is True


def test_multiple_roots_with_comments():
    assert has_single_root("<div></div><!-- c --><div></div>") is False


def test_multiple_roots_with_django_logic():
    template = """
    {% if cond %}
        <div>One</div>
    {% endif %}
    <div>Two</div>
    """
    # Preprocessing removes {% ... %}, so this becomes:
    # <div>One</div>
    # <div>Two</div>
    # Which has two roots.
    assert has_single_root(template) is False
