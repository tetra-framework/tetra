---
title: Click to Edit
---

# Click to Edit

The click-to-edit pattern enables inline editing of a record without refreshing the page.

This is a simple way to implement this as Tetra component, including save/cancel buttons:
```python
@default.register
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

    template: django_html = """
    <div>
        {% if edit_mode %}
            <div class='input-group'>
                <input class="form-control" type="text" x-model="name"/>
                <button class="btn btn-outline-danger" type="button"
                @click="cancel()"><i class='fa fa-undo'></i></button>
                <button class="btn btn-outline-secondary" type="button"
                @click="save()">Save</button>
            </div>
        {% else %}
            <div @click="edit()" role="button">Name: {{name}}</div>
        {% endif %}
    </div>
    """
```

If you click the text, it is replaced with an input form field.

You could also imagine to do that in other ways:

* by hiding the borders of the input field in display mode, and showing them again using Alpine when in edit_mode.
* without buttons, just by using the `@blur` event for saving.