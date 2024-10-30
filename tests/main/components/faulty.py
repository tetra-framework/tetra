from tetra import Component
from .base import faulty

# This module contains some Components that are faulty.
# We cannot add faulty Python code at module level, as this would affect all other
# components' tests. So we place some syntax/import/etc. errors into the components'
# __init__ method so the errors occur when the components itself are imported.


@faulty.register
class FaultyComponent1(Component):
    def __init__(self, *args, **kwargs):
        import foo_bar_not_existing_module


@faulty.register
class FaultyComponent2(Component):
    def __init__(self, *args, **kwargs):
        foo  #  This must raise a NameError
