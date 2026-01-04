#!/bin/bash

# Find project directory by looking for pyproject.toml with 'name = "tetra"'
# this is somehow "unsafe" as one could place a malicious pyproject.toml in the path upwards.
# But this is only used during development. If you don't control your dev environment, you've got some
# problems anyway.
find_project_dir() {
    local current_dir="$(pwd)"

    while [[ "$current_dir" != "/" ]]; do
        if [[ -f "$current_dir/pyproject.toml" ]] && grep -q 'name = "tetra"' "$current_dir/pyproject.toml"; then
            echo "$current_dir"
            return 0
        fi
        current_dir="$(dirname "$current_dir")"
    done

    echo "Error: Could not find pyproject.toml with 'name = \"tetra\"'" >&2
    return 1
}

project_dir=$(find_project_dir)
if [[ $? -ne 0 ]]; then
    echo "No tetra project directory found. Exiting."
    exit 1
fi

cd "$project_dir"


node_modules/.bin/esbuild src/tetra/js/tetra.js --bundle --sourcemap --target=chrome80,firefox73,safari13,edge80 --outfile=src/tetra/static/tetra/js/tetra.js
node_modules/.bin/esbuild src/tetra/js/tetra.js --bundle --minify --sourcemap --target=chrome80,firefox73,safari13,edge80 --outfile=src/tetra/static/tetra/js/tetra.min.js