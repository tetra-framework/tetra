from tetra import Component, public


class TodoItem(Component):
    title = public("")
    done = public(False)

    def load(self, todo, *args, **kwargs):
        self.todo = todo
        self.title = todo.title
        self.done = todo.done

    @public.watch("title", "done")
    @public.debounce(200)
    def save(self, value, old_value, attr):
        self.todo.title = self.title
        self.todo.done = self.done
        self.todo.save()

    @public(update=False)
    def delete_item(self):
        self.todo.delete()
        self.client._removeComponent()
