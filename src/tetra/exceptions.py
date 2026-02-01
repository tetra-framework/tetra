class ComponentError(Exception):
    pass


class ComponentNotFound(ComponentError):
    pass


class LibraryError(Exception):
    pass


class ProtocolError(Exception):
    """Error in the Tetra HTTP protocol."""

    pass
