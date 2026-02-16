class ComponentError(Exception):
    pass


class ComponentNotFound(ComponentError):
    pass


class LibraryError(Exception):
    pass


class ProtocolError(Exception):
    """Error in the Tetra HTTP protocol."""

    pass


class StaleComponentStateError(ComponentError):
    """Component state references data that no longer exists.

    This exception is raised when a component's load() method fails because
    database objects or other resources it depends on have been deleted or
    are no longer available. This typically happens in multi-client scenarios
    where one client deletes data that another client's component still references.
    """

    pass
