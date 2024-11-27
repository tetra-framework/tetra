from tetra import Component
from .base import faulty

# This module contains some Components that are faulty.
# We cannot add faulty Python code at module level, as this would affect all other
# components' tests. So we place some syntax/import/etc. errors into the components'
# __init__ method so the errors occur when the components itself are imported.


@faulty.register
class FaultyComponent1(Component):
    template = "<div></div>"

    def __init__(self, *args, **kwargs):  # noqa
        import foo_bar_not_existing_module  # noqa

@faulty.register
class FaultyComponent2(Component):
    template = "<div></div>"

    def __init__(self, *args, **kwargs):  # noqa
        foo  # noqa; This must raise a NameError


class FaultyComponent3(Component):
    # this component has no html tag as root element in the template
    template = "foo"

