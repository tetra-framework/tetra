"""Full stack component framework for Django using Alpine.js"""

from .components import BasicComponent, Component, ReactiveComponent, public
from .library import Library

__all__ = [BasicComponent, Component, ReactiveComponent, public, Library]
__version__ = "0.5.1"
__version_info__ = tuple([int(num) for num in __version__.split(".")])
