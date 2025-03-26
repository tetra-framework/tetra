from tetra import Component, public


class DisableButton(Component):

    # update=False, because in the demo, we don't want to refresh the component,
    # as the button would be re-enabled then.
    @public(update=False)
    def submit(self):
        pass
