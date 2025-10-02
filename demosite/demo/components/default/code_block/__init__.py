from tetra import BasicComponent


class CodeBlock(BasicComponent):
    title: str = ""
    file_name: str = ""
    language: str = "django"

    def load(
        self,
        title: str = "",
        file_name: str = None,
        language: str = None,
        *args,
        **kwargs,
    ) -> None:
        self.title = title
        self.file_name = file_name or ""
        self.language = language or ""
