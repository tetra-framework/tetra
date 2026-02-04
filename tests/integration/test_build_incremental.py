import os
import time
import json
import shutil
from unittest.mock import patch
from django.apps import AppConfig
from tetra import Library, Component
from tetra.build import build


def test_incremental_build(tmp_path, current_app):
    # Setup a mock app path
    app_path = tmp_path / "test_app"
    app_path.mkdir()
    (app_path / "static").mkdir()

    # Mock AppConfig
    class MockAppConfig:
        def __init__(self, path, label):
            self.path = str(path)
            self.label = label

    mock_app = MockAppConfig(app_path, "test_app")

    # Create a component file
    comp_file = app_path / "components.py"
    comp_file.write_text(
        "from tetra import Component\nclass MyComponent(Component):\n    script = 'console.log(1)'"
    )

    # Define component class manually to control its source location
    class MyComponent(Component):
        template = "<div></div>"
        script = "console.log(1)"

        @classmethod
        def has_styles(cls):
            return False

        @classmethod
        def get_source_location(cls):
            return str(comp_file), 0, 3

    # Create Library and register component
    lib = Library("test_lib", app=mock_app)
    lib.components = {"my_component": MyComponent}
    MyComponent._library = lib

    # First build
    with patch("tetra.library.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        # Mocking esbuild output file creation
        def side_effect(*args, **kwargs):
            out_dir = None
            for arg in args[0]:
                if arg.startswith("--outdir="):
                    out_dir = arg.split("=")[1]
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
                js_hashed = "test_lib-HASH.js"
                css_hashed = "test_lib-HASH.css"
                with open(os.path.join(out_dir, js_hashed), "w") as f:
                    f.write("built")
                with open(os.path.join(out_dir, css_hashed), "w") as f:
                    f.write("built")

                # Create .filename files
                with open(lib.js_path + ".filename", "w") as f:
                    f.write(js_hashed)
                with open(lib.styles_path + ".filename", "w") as f:
                    f.write(css_hashed)

            # Create meta file as esbuild would
            meta_file = None
            for arg in args[0]:
                if arg.startswith("--metafile="):
                    meta_file = arg.split("=")[1]
            if meta_file:
                os.makedirs(os.path.dirname(meta_file), exist_ok=True)
                with open(meta_file, "w") as f:
                    json.dump(
                        {
                            "outputs": {
                                os.path.join(out_dir, "test_lib.js"): {
                                    "entryPoint": "something"
                                }
                            }
                        },
                        f,
                    )
            return mock_run.return_value

        mock_run.side_effect = side_effect

        lib.build()
        assert (
            mock_run.call_count == 2
        )  # one for JS, one for CSS (actually build_styles also calls esbuild if there are styles)
        # In this case MyComponent only has script, so build_styles won't call esbuild unless it has styles.
        # Wait, build_styles in library.py:
        # if any component has styles: call esbuild.

    # Second build - should skip
    with patch("tetra.library.subprocess.run") as mock_run:
        lib.build()
        mock_run.assert_not_called()

    # Modify source file
    time.sleep(0.1)  # ensure mtime change
    # Update MyComponent.script to match new file content
    MyComponent.script = "console.log(2)"
    comp_file.write_text(
        "from tetra import Component\nclass MyComponent(Component):\n    script = 'console.log(2)'"
    )

    # Third build - should run again
    with patch("tetra.library.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.side_effect = side_effect
        lib.build()
        assert mock_run.called
