from tetra import Component, public


class ClickToEdit(Component):
    name = public("John Doe")
    old_name = ""
    edit_mode: bool = public(False)

    @public
    def edit(self):
        self.old_name = self.name
        self.edit_mode = True

    @public
    def save(self):
        """save `self.name` into a model"""
        self.edit_mode = False

    @public
    def cancel(self):
        self.name = self.old_name
        self.edit_mode = False

    @public
    def reset(self):
        self.name = self.old_name
