from tetra import BasicComponent


class CodeBlock(BasicComponent):
    title: str = ""
    file_name: str = ""
    language: str = "django"

    def load(
        self, file_name: str, language: str, title: str = "", *args, **kwargs
    ) -> None:
        self.title = title
        self.file_name = file_name
        self.language = language
