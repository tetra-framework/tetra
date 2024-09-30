---
title: Delete Row
---

# Delete Row

Here's an example component demonstrating how to create a delete button that removes a table row when clicked.
```python
@examples.register
class DeleteRowTable(Component):
    def load(self):
        # we reuse the ToDo items from Tetra's front page here...
        self.rows = ToDo.objects.filter(session_key=self.request.session.session_key)

    template: django_html = """
    <table class='table'>
    <thead>
        <tr>
            <th>Title</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for row in rows %}
            {% @ demo.examples.DeleteRow row=row key=row.id / %}
        {% endfor %}
    </tbody>
    </table>
    """
```
So far for the table component. The rows are components themselves:
```python
@examples.register
class DeleteRow(Component):
    title = public("")

    def load(self, row):
        self.row = row
        self.title = row.title

    @public(update=False)
    def delete_item(self):
        # self.row.delete()  # delete the item in the DB here!
        self.client._removeComponent() # remove component from DOM

    template: django_html = """
    <tr {% ... attrs %}>
        <td>{{ title }}</td>
        <td>
            <button @click="delete_item()" class="btn btn-sm">
                <i class="fa-solid fa-trash"></i>
            </button>
        </td>
    </tr>
    """
```