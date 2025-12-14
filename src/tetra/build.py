import itertools
import os
import shutil
import glob
from django.conf import settings
from tetra import Library


def build(libs_to_build):
    # TODO: only build files if code has changed

    # Clear old static files before building
    if hasattr(settings, "STATIC_ROOT") and settings.STATIC_ROOT:
        tetra_pattern = os.path.join(settings.STATIC_ROOT, "*/tetra/")
        for tetra_dir in glob.glob(tetra_pattern):
            if os.path.exists(tetra_dir):
                print(f"Clearing old static files: {tetra_dir}")
                shutil.rmtree(tetra_dir)

    print("Tetra: Building Javascript and CSS")
    print(" - Libraries: %s" % ",".join(o.display_name for o in libs_to_build))
    for lib in libs_to_build:
        lib.build()


def runserver_build():
    libs_to_build = list(
        itertools.chain.from_iterable(d.values() for d in Library.registry.values())
    )
    build(libs_to_build)
