from tetra import BasicComponent


class ShowCase(BasicComponent):
    title: str = ""

    def load(self, title: str = "", *args, **kwargs):
        self.title = title
