import pytest
from tetra import BasicComponent, Library


class BasicComponentWithInlineScript(BasicComponent):
    template = """<div><button onclick="testFunc()">Click</button></div>"""
    script = "function testFunc() { console.log('test'); }"


class BasicComponentWithoutScript(BasicComponent):
    template = """<div>No script</div>"""


def test_basic_component_has_script():
    """Verify that BasicComponent.has_script() returns True when script is defined."""
    assert BasicComponentWithInlineScript.has_script() is True
    assert BasicComponentWithoutScript.has_script() is False


def test_basic_component_is_script_inline():
    """Verify that BasicComponent._is_script_inline() correctly detects inline scripts."""
    assert BasicComponentWithInlineScript._is_script_inline() is True
    assert BasicComponentWithoutScript._is_script_inline() is False


def test_basic_component_extract_script():
    """Verify that BasicComponent.extract_script() returns the script content."""
    script = BasicComponentWithInlineScript.extract_script()
    assert "function testFunc()" in script
    assert "console.log('test')" in script


def test_basic_component_render_script():
    """Verify that BasicComponent.render_script() returns raw JavaScript without Alpine wrapper."""
    script = BasicComponentWithInlineScript.render_script()
    # Should contain the raw JavaScript
    assert "function testFunc()" in script
    # Should NOT contain Alpine.js component registration code
    assert "Tetra.makeAlpineComponent" not in script
    assert "alpine:init" not in script


def test_basic_component_render_script_with_component_var():
    """Verify that BasicComponent.render_script() uses component_var when provided."""
    custom_script = "function customFunc() { return 42; }"
    result = BasicComponentWithInlineScript.render_script(component_var=custom_script)
    assert result == custom_script


def test_basic_component_render_script_empty():
    """Verify that BasicComponent.render_script() returns empty string when no script."""
    result = BasicComponentWithoutScript.render_script()
    assert result == ""
