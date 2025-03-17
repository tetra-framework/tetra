from tetra import Component

# This library contains some Components that are faulty.
# We cannot add faulty Python code at module level, as this would affect all other
# components' tests. So we place some syntax/import/etc. errors into the components'
# __init__ method so the errors occur when the components itself are imported.


class FaultyComponent1(Component):
    template = "<div></div>"

    def __init__(self, _request, *args, **kwargs):  # noqa
        import foo_bar_not_existing_module

    def __init__(self, *args, **kwargs):  # noqa
        import foo_bar_not_existing_module  # noqa


class FaultyComponent2(Component):
    template = "<div></div>"

    def __init__(self, _request, *args, **kwargs):  # noqa
        #  This must raise a NameError
        foo  # noqa


class FaultyComponent3(Component):
    # this component has no html tag as root element in the template
    template = "foo"
