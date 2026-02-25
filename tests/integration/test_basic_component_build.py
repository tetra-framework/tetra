"""Integration test for BasicComponent with JavaScript support."""
import os
import tempfile
from pathlib import Path

import pytest
from tetra import BasicComponent, Library


@pytest.fixture
def test_library(current_app, tmp_path):
    """Create a temporary library for testing."""
    lib = Library("test_basic_js", current_app)
    # Override the cache path to use tmp_path
    original_cache = os.environ.get("TETRA_CACHE_PATH")
    os.environ["TETRA_CACHE_PATH"] = str(tmp_path / "cache")
    yield lib
    # Restore original cache path
    if original_cache:
        os.environ["TETRA_CACHE_PATH"] = original_cache
    else:
        os.environ.pop("TETRA_CACHE_PATH", None)


def test_basic_component_with_inline_js_build(test_library):
    """Test that BasicComponent with inline JS is properly built."""

    @test_library.register
    class TestBasicWithJS(BasicComponent):
        template = """<div onclick="handleClick()">Click me</div>"""
        script = """
        function handleClick() {
            console.log('BasicComponent click handled!');
            return true;
        }
        """

    # Verify the component is registered
    assert "test_basic_with_js" in test_library.components

    # Verify has_script returns True
    assert TestBasicWithJS.has_script() is True

    # Verify extract_script returns the script
    script_content = TestBasicWithJS.extract_script()
    assert "handleClick" in script_content
    assert "console.log" in script_content

    # Verify render_script returns raw JS (no Alpine wrapper)
    rendered = TestBasicWithJS.render_script()
    assert "handleClick" in rendered
    assert "Tetra.makeAlpineComponent" not in rendered
    assert "alpine:init" not in rendered


def test_basic_component_without_js(test_library):
    """Test that BasicComponent without JS works correctly."""

    @test_library.register
    class TestBasicNoJS(BasicComponent):
        template = """<div>No JavaScript</div>"""

    assert "test_basic_no_js" in test_library.components
    assert TestBasicNoJS.has_script() is False
    assert TestBasicNoJS.render_script() == ""


def test_basic_component_with_css_and_js(test_library):
    """Test that BasicComponent can have both CSS and JS."""

    @test_library.register
    class TestBasicBoth(BasicComponent):
        template = """<div class="styled" onclick="doSomething()">Both</div>"""
        style = ".styled { color: blue; }"
        script = "function doSomething() { alert('test'); }"

    assert TestBasicBoth.has_script() is True
    assert TestBasicBoth.has_styles() is True

    script = TestBasicBoth.extract_script()
    assert "doSomething" in script

    styles = TestBasicBoth.extract_styles()
    assert "styled" in styles
    assert "color: blue" in styles
