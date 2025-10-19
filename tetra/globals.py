# This is set to True if any ReactiveComponent is initialized
_has_reactive_components = False


def has_reactive_components() -> bool:
    """Check if any reactive components have been registered."""
    return _has_reactive_components
