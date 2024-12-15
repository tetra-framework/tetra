from tetra import Component, public


class DeleteRow(Component):
    title: str = public("")

    def load(self, row, *args, **kwargs):
        self.row = row
        self.title = row.title

    @public(update=False)
    def delete_item(self):
        # self.row.delete()  # delete the item in the DB here!
        self.client._removeComponent()
