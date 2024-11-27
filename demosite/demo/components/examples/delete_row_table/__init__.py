from demo.models import ToDo
from tetra import Component


class DeleteRowTable(Component):
    def load(self):
        self.rows = ToDo.objects.filter(session_key=self.request.session.session_key)
