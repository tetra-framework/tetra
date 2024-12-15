from sourcetypes import django_html

from demo.models import ToDo
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
    def discard(self):
        self.name = self.old_name
        self.edit_mode = False

    # language=html
    template: django_html = """
    <div>
        {% if edit_mode %}
            <div class='input-group'>
                <input class="form-control" type="text" x-model="name"/>
                <button class="btn btn-outline-danger" type="button"
                @click="discard()"><i class='fa fa-undo'></i></button>
                <button class="btn btn-outline-secondary" type="button"
                @click="save()">Save</button>
            </div>
        {% else %}
            <div @click="edit()" role="button">Name: {{name}}</div>
        {% endif %}
    </div>
    """


class DeleteRowTable(Component):
    def load(self):
        self.rows = ToDo.objects.filter(session_key=self.request.session.session_key)

    # language=html
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


class DeleteRow(Component):
    title = public("")

    def load(self, row):
        self.row = row
        self.title = row.title

    @public(update=False)
    def delete_item(self):
        # self.row.delete()
        self.client._removeComponent()

    # language=html
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
