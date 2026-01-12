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


# Determine the bundled esbuild path
system=$(uname -s)
machine=$(uname -m)
plat_key=""

if [[ "$system" == "Linux" ]]; then
    if [[ "$machine" == "x86_64" ]]; then
        plat_key="linux-x64"
    elif [[ "$machine" == "aarch64" || "$machine" == "arm64" ]]; then
        plat_key="linux-arm64"
    fi
elif [[ "$system" == "Darwin" ]]; then
    if [[ "$machine" == "x86_64" ]]; then
        plat_key="darwin-x64"
    elif [[ "$machine" == "arm64" ]]; then
        plat_key="darwin-arm64"
    fi
elif [[ "$system" == "MINGW"* || "$system" == "MSYS"* || "$system" == "CYGWIN"* ]]; then
    if [[ "$machine" == "x86_64" ]]; then
        plat_key="windows-x64"
    elif [[ "$machine" == "ARM64" ]]; then
        plat_key="windows-arm64"
    fi
fi

if [[ -n "$plat_key" ]]; then
    if [[ "$system" == "MINGW"* || "$system" == "MSYS"* || "$system" == "CYGWIN"* ]]; then
        esbuild_bin="src/tetra/bin/esbuild.exe-$plat_key"
    else
        esbuild_bin="src/tetra/bin/esbuild-$plat_key"
    fi
fi

if [[ ! -f "$esbuild_bin" ]]; then
    # Fallback to system esbuild
    esbuild_bin="esbuild"
fi

echo "Using esbuild at: $esbuild_bin"

"$esbuild_bin" src/tetra/js/tetra.js --bundle --sourcemap --target=chrome80,firefox73,safari13,edge80 --outfile=src/tetra/static/tetra/js/tetra.js
"$esbuild_bin" src/tetra/js/tetra.js --bundle --minify --sourcemap --target=chrome80,firefox73,safari13,edge80 --outfile=src/tetra/static/tetra/js/tetra.min.js