# This is set to True if any ReactiveComponent is initialized
_has_reactive_components: bool = False


@property
def has_reactive_components():
    return _has_reactive_components


@has_reactive_components.setter
def has_reactive_components(value: bool):
    _has_reactive_components = value
