import pytest

from tests.main.helpers import render_component_tag
from tetra.exceptions import ComponentError, ComponentNotFound


def test_error_when_using_missing_component(request):
    """If a component itself is not found, a ComponentNotFound exception must be
    raised."""
    with pytest.raises(ComponentNotFound):
        render_component_tag(request, "{% @ main.faulty.NotExistingComponent / %}")


def test_component_importing_missing_module(request):
    """if the imported component itself imports a non-existing (e.g. not installed)
    python module, a ModuleNotFoundError must be raised."""
    with pytest.raises(ModuleNotFoundError) as exc_info:
        render_component_tag(request, "{% @ main.faulty.FaultyComponent1 / %}")

    assert exc_info.value.msg == "No module named 'foo_bar_not_existing_module'"


def test_component_with_name_error(request):
    """If a component calls not-existing code, this must be raised transparently."""
    with pytest.raises(NameError):
        render_component_tag(request, "{% @ main.faulty.FaultyComponent2 / %}")


def test_component_with_no_root_tag(request):
    """If a component calls not-existing code, this must be raised transparently."""
    with pytest.raises(ComponentError):
        render_component_tag(request, "{% @ main.faulty.faulty_component3 / %}")
