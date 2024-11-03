from demo.models import ToDo
from tetra import Component, public


class DeleteRow(Component):
    title = public("")

    def load(self, row):
        self.row = row
        self.title = row.title

    @public(update=False)
    def delete_item(self):
        # self.row.delete()
        self.client._removeComponent()
