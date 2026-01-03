# TODO evaluate moving to dispatcher
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tetra import ReactiveComponent

registry: dict[str, list["ReactiveComponent"]] = {}
