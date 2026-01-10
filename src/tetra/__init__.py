"""Full stack component framework for Django using Alpine.js"""

from .components import BasicComponent, Component, public
from .library import Library

__all__: list[str] = [
    "BasicComponent",
    "Component",
    "public",
    "Library",
    "Router",
    "Link",
    "Redirect",
]

try:
    import channels  # noqa

    __all__.append("ReactiveComponent")
except ImportError:
    pass


def __getattr__(name):
    if name in ("Router", "Link", "Redirect"):
        from tetra.router import Redirect
        from tetra.router import Link
        from tetra.router import Router

        if name == "Router":
            return Router
        if name == "Link":
            return Link
        if name == "Redirect":
            return Redirect
    if name == "ReactiveComponent":
        try:
            import channels  # noqa
        except ImportError:
            raise ImportError(
                "ReactiveComponent requires 'channels' to be installed. "
                "Please install it with: pip install channels"
            ) from None
        from .components.reactive import ReactiveComponent

        return ReactiveComponent
    raise AttributeError(f"module {__name__} has no attribute {name}")


__version__ = "0.6.10"
__version_info__ = tuple([num for num in __version__.split(".")])
