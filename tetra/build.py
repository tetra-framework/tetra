import itertools
from .component_register import libraries


def build(libs_to_build):
    print("Tetra: Building Javascript and CSS")
    print(f" - Libraries: %s" % ",".join(o.display_name for o in libs_to_build))
    for lib in libs_to_build:
        lib.build()


def runserver_build():
    libs_to_build = list(
        itertools.chain.from_iterable(d.values() for d in libraries.values())
    )
    build(libs_to_build)
