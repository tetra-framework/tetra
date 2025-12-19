"""Full stack component framework for Django using Alpine.js"""

from .components import BasicComponent, Component, public
from .library import Library

__all__: list = []

try:
    # if channels is available, ReactiveComponent can be imported, so try it
    # and fail silently if it does not work.
    from tetra.components.reactive import ReactiveComponent

    __all__ += [ReactiveComponent]
except ImportError:
    pass

__all__ += [BasicComponent, Component, public, Library]
__version__ = "0.5.3"
__version_info__ = tuple([int(num) for num in __version__.split(".")])
