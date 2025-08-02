from demo.models import ToDo
from tetra import Component, public


class TodoList(Component):
    title = public("")

    def load(self, *args, **kwargs):
        self.todos = ToDo.objects.filter(
            session_key=self.request.session.session_key,
        )

    @public
    def add_todo(self, title: str):
        if self.title:
            todo = ToDo(
                title=title,
                session_key=self.request.session.session_key,
            )
            todo.save()
            self.title = ""
