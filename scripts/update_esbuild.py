import sys
from pathlib import Path
import logging

# Add src to sys.path to import tetra.conf
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tetra.conf import download_esbuild

logging.basicConfig(level=logging.INFO)

BIN_DIR = Path(__file__).parent.parent / "src" / "tetra" / "bin"


def download_all_platforms():
    platforms = [
        "linux-x64",
        "linux-arm64",
        "darwin-x64",
        "darwin-arm64",
        "windows-x64",
        "windows-arm64",
    ]

    for plat_key in platforms:
        bin_name = "esbuild.exe" if "windows" in plat_key else "esbuild"
        dest_path = BIN_DIR / f"{bin_name}-{plat_key}"
        if dest_path.exists():
            print(f"{plat_key} already exists.")
            continue

        try:
            download_esbuild(plat_key, dest_path)
        except Exception as e:
            print(f"Failed to download {plat_key}: {e}")


if __name__ == "__main__":
    download_all_platforms()
