"""Test that context is available for rendering but not saved to component state."""

import pytest
from tetra.helpers import render_component_tag
from bs4 import BeautifulSoup
from unittest.mock import Mock


class UnpickleableObject:
    """An object that cannot be pickled."""

    def __reduce__(self):
        raise TypeError("This object cannot be pickled")


@pytest.mark.django_db
def test_context_available_but_not_pickled(tetra_request):
    """Test that outer context is available in slots but doesn't get pickled."""

    # Create an unpickleable object
    unpickleable = UnpickleableObject()

    # This should render successfully even though the context contains
    # an unpickleable object, because _context is excluded from state
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithDefaultBlock context: test_var %}"
        "{{test_var}}"
        "{% /SimpleComponentWithDefaultBlock %}",
        context={"test_var": "success", "unpickleable": unpickleable},
    )

    # The context variable should be available in the slot
    soup = BeautifulSoup(content, "html.parser")
    component = soup.find("div")
    assert component is not None
    assert "success" in str(content)


@pytest.mark.django_db
def test_explicit_context_with_unpickleable_renders(tetra_request):
    """Test that even with explicit context: args, unpickleable objects in outer
    context don't cause issues since _context is excluded from state."""

    # Create an unpickleable object
    unpickleable = UnpickleableObject()

    # Even when explicitly passing context variables, the _context itself
    # (which contains the unpickleable object) won't be pickled
    content = render_component_tag(
        tetra_request,
        component_string="{% SimpleComponentWithDefaultBlock context: test_var %}"
        "{{test_var}}"
        "{% /SimpleComponentWithDefaultBlock %}",
        context={"test_var": "works", "unpickleable": unpickleable},
    )

    soup = BeautifulSoup(content, "html.parser")
    component = soup.find("div")
    assert component is not None
    assert "works" in str(content)
