import pytest
from tetra.components.utils import get_next_autokey, _tetra_component_count


def test_autokey_persistence():
    # Simulate first request
    if hasattr(_tetra_component_count, "count"):
        del _tetra_component_count.count

    k1 = get_next_autokey()
    assert k1 == "tk_1"
    k2 = get_next_autokey()
    assert k2 == "tk_2"

    # Simulate second request in same thread
    # The counter stays at 2!
    k3 = get_next_autokey()
    assert k3 == "tk_3"


def test_autokey_reset_needed():
    if hasattr(_tetra_component_count, "count"):
        del _tetra_component_count.count

    # We want it to be reset for each request to ensure stability
    # but if it's NOT reset, then different requests get different IDs
    # which is actually BETTER for uniqueness, but WORSE for stability (morphing).

    k1 = get_next_autokey()
    # ...
