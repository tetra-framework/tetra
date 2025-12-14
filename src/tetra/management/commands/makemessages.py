import ast
import os

from django.core.management.commands.makemessages import (
    Command as MakeMessagesCommand,
    BuildFile,
)
from django.utils.functional import cached_property


def mark_for_translation(s):
    """Mark a string for translation without translating it immediately."""
    from django.utils.translation import gettext_noop

    return gettext_noop(s)


class TetraBuildFile(BuildFile):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inline_templates: dict[int, str] = {}

    @cached_property
    def is_templatized(self):
        if self.domain == "django":
            file_ext = os.path.splitext(self.translatable.file)[1]
            if file_ext == ".py" and (
                self.translatable.file == "components.py"
                or "components" in self.translatable.dirpath
            ):
                # FIXME: find a proper way to quickly find out if this file contains
                #  Tetra components.
                with open(self.translatable.path, "r") as file:
                    content = file.read()
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if not isinstance(node, ast.ClassDef):
                                continue
                            has_component_base = False
                            # FIXME: use better way to find out if this is a
                            #  Tetra component
                            # it could be "tetra.components.Component", or
                            # "tetra.Component", or a custom "FooComponent" named
                            # in another way. We just check for the
                            # name ending in "Component" which is a bit dull...
                            for base in node.bases:
                                if isinstance(base, ast.Name) and base.id.endswith(
                                    "Component"
                                ):
                                    has_component_base = True
                            if has_component_base:
                                for stmt in node.body:
                                    targets = []
                                    if isinstance(stmt, ast.Assign):
                                        targets = stmt.targets
                                    elif isinstance(stmt, ast.AnnAssign):
                                        targets = [stmt.target]
                                    for target in targets:
                                        if (
                                            isinstance(target, ast.Name)
                                            and target.id == "template"
                                        ):
                                            # stmt.value.s now is the
                                            # template html string which may
                                            # contain translatable strings
                                            self.inline_templates[target.lineno] = (
                                                stmt.value.s
                                            )
                                            # if there is at least one
                                            # template in the component,
                                            # consider the component file
                                            # templatized.
                                            return True

                    except SyntaxError | SyntaxWarning:
                        # in case of syntax errors/warnings, just ignore this file
                        return False
        return super().is_templatized

    def __repr_(self):
        return "<%s: %s>" % (self.__class__.__name__, self.translatable.path)


class Command(MakeMessagesCommand):
    """Django's makemessages command which includes .py files that contain inline
    templates within Tetra components."""

    build_file_class = TetraBuildFile
