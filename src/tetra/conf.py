import logging
import urllib.request
import json
import tarfile
import shutil
from typing import Any

from django.conf import settings
from pathlib import Path
import platform
import os
from . import default_settings

logger = logging.getLogger(__name__)

# The version of esbuild to use
ESBUILD_VERSION = "0.27.2"


def get_setting(name) -> Any:
    if hasattr(settings, name):
        return getattr(settings, name)
    return getattr(default_settings, name, None)


def download_esbuild(plat_key: str, dest_path: Path):
    """
    Downloads esbuild for the given platform.
    """
    platforms = {
        "linux-x64": "@esbuild/linux-x64",
        "linux-arm64": "@esbuild/linux-arm64",
        "darwin-x64": "@esbuild/darwin-x64",
        "darwin-arm64": "@esbuild/darwin-arm64",
        "windows-x64": "@esbuild/win32-x64",
        "windows-arm64": "@esbuild/win32-arm64",
    }

    if plat_key not in platforms:
        raise Exception(f"Unsupported platform for esbuild: {plat_key}")

    npm_package = platforms[plat_key]
    url = f"https://registry.npmjs.org/{npm_package}/-/{npm_package.split('/')[-1]}-{ESBUILD_VERSION}.tgz"

    logger.info(f"Tetra: Downloading esbuild for {plat_key} from {url}")

    temp_tgz = dest_path.parent / f"{plat_key}.tgz"
    try:
        urllib.request.urlretrieve(url, temp_tgz)

        # Extract
        extract_dir = dest_path.parent / f"temp_{plat_key}"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)

        with tarfile.open(temp_tgz, "r:gz") as tar:
            tar.extractall(path=extract_dir)

        bin_name = "esbuild.exe" if "windows" in plat_key else "esbuild"

        # Find the binary in extract_dir
        found_bin = None
        for p in extract_dir.rglob(bin_name):
            found_bin = p
            break

        if found_bin:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(found_bin), str(dest_path))
            if "windows" not in plat_key:
                dest_path.chmod(0o755)
            logger.info(f"Tetra: Installed esbuild to {dest_path}")
        else:
            raise Exception(f"Could not find {bin_name} in downloaded archive")

    finally:
        if temp_tgz.exists():
            temp_tgz.unlink()
        if "extract_dir" in locals() and extract_dir.exists():
            shutil.rmtree(extract_dir)


def get_esbuild_path() -> str:
    # User override in settings.py
    if hasattr(settings, "TETRA_ESBUILD_PATH"):
        return settings.TETRA_ESBUILD_PATH

    # Detect platform for bundled binary
    system = platform.system()
    machine = platform.machine()
    plat_key = None
    if system == "Linux":
        if machine == "x86_64":
            plat_key = "linux-x64"
        elif machine in ("aarch64", "arm64"):
            plat_key = "linux-arm64"
    elif system == "Darwin":
        if machine == "x86_64":
            plat_key = "darwin-x64"
        elif machine == "arm64":
            plat_key = "darwin-arm64"
    elif system == "Windows":
        if machine == "AMD64":
            plat_key = "windows-x64"
        elif machine == "ARM64":
            plat_key = "windows-arm64"

    bin_name = "esbuild"
    if system == "Windows":
        bin_name = "esbuild.exe"

    bundled_bin = None
    if plat_key:
        bundled_bin = Path(__file__).parent / "bin" / f"{bin_name}-{plat_key}"

        if bundled_bin.exists():
            return str(bundled_bin)

        # Try to download if it doesn't exist
        try:
            download_esbuild(plat_key, bundled_bin)
            if bundled_bin.exists():
                return str(bundled_bin)
        except Exception as e:
            logger.error(f"Tetra: Failed to download esbuild: {e}")

    # Fallback to node_modules
    if system == "Windows":
        bin_name = "esbuild.cmd"
    else:
        bin_name = "esbuild"

    if hasattr(settings, "BASE_DIR") and settings.BASE_DIR:
        node_bin = Path(settings.BASE_DIR) / "node_modules" / ".bin" / bin_name
        if node_bin.exists():
            return str(node_bin)

    return bin_name
