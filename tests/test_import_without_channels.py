import sys
import pytest
from unittest.mock import patch


def test_import_tetra_without_channels():
    """
    Test that tetra can be imported without channels,
    but 'from tetra import ReactiveComponent' fails.
    """
    # Clear tetra from sys.modules
    to_delete = [name for name in sys.modules if name.startswith("tetra")]
    for name in to_delete:
        del sys.modules[name]

    # Mock 'channels' as missing
    with patch.dict(sys.modules, {"channels": None}):
        import tetra

        assert tetra.__name__ == "tetra"

        with pytest.raises(ImportError) as excinfo:
            from tetra import ReactiveComponent  # noqa

        assert "ReactiveComponent requires 'channels'" in str(excinfo.value)


def test_reactivecomponent_not_in_tetra_star_exports():
    """Testing star import with channels mocked as missing..."""
    with patch.dict(sys.modules, {"channels": None}):
        # We need to clear tetra from sys.modules to force re-import under mock
        if "tetra" in sys.modules:
            del sys.modules["tetra"]
        if "tetra.components" in sys.modules:
            del sys.modules["tetra.components"]

        import tetra

        assert "ReactiveComponent" not in tetra.__all__
