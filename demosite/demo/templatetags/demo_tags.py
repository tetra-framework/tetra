import os.path

from django import template
from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe, SafeString
from django.template.loaders.app_directories import Loader
import tetra
from tetra.component_register import resolve_component

register = template.Library()


@register.simple_tag
def tetra_version() -> str:
    return tetra.__version__


@register.simple_tag
def include_source(file_name, start=None, end=None) -> SafeString:
    error = None
    for origin in Loader(None).get_template_sources(file_name):
        try:
            with open(origin.name) as f:
                text = f.read()
                if (start is not None) or (end is not None):
                    text = "\n".join(text.split("\n")[start:end])
                return mark_safe(escape(text))
        except FileNotFoundError as e:
            error = e
            pass
    if error:
        raise error
    return mark_safe("")


@register.simple_tag
def md_include_source(filename: str, first_line_comment: str = "") -> SafeString:
    """Includes the source code of a file, rlative to the demo root directory.

    It returns a SafeString version of the file content, surrounded with
    MarkDown triple-quote syntax including language hint,
    so you can include the result directly in a markdown file:

    {% md_include_source "path/to/file.py" "# some title" %}

    You can provide a title for the code block. If no title is provided, the filename
    itself is used.
    """
    ext = os.path.splitext(filename)[1]
    basename = os.path.basename(filename)
    if basename == "__init__.py":
        # "__init__.py" isn't very explanative.
        # So use the containing directory name + basename
        basename = (
            f"{os.path.basename(os.path.dirname(filename))}/"
            f"{os.path.basename(filename)}"
        )
    try:
        with open(settings.BASE_DIR / filename) as f:
            content = f.read()
    except FileNotFoundError as e:
        return mark_safe(f"File not found: {filename}")

    language = ""
    if ext == ".html":
        language = "django"
        first_line_comment = f"<!-- {first_line_comment or basename} -->\n"
    elif ext == ".py":
        language = "python"
        first_line_comment = f"# {first_line_comment or basename}\n"
    elif ext == ".css":
        language = "css"
        first_line_comment = f"// {first_line_comment or basename}\n"
    elif ext == ".js":
        language = "javascript"
        first_line_comment = f"// {first_line_comment or basename}\n"
    return mark_safe(f"```{language}\n{first_line_comment}{content}\n```")


@register.simple_tag
def md_include_component_source(
    component_name: str, first_line_comment: str = ""
) -> SafeString:
    component = resolve_component(None, component_name)
    if not component:
        raise template.TemplateSyntaxError(
            f"Unable to resolve dynamic component: '{component_name}'"
        )
    return md_include_source(component.get_source_location()[0], first_line_comment)


@register.simple_tag
def md_include_component_template(
    component_name: str, first_line_comment: str = ""
) -> SafeString:
    component = resolve_component(None, component_name)
    if not component:
        raise template.TemplateSyntaxError(
            f"Unable to resolve dynamic component: '{component_name}'"
        )
    return md_include_source(
        component.get_template_source_location()[0], first_line_comment
    )


@register.simple_tag
def include_source_part(file_name, part=0):
    error = None
    for origin in Loader(None).get_template_sources(file_name):
        try:
            with open(origin.name) as f:
                text = f.read().split("# SPLIT")
                text = text[part].rstrip().lstrip("\n")
                return mark_safe(escape(text))
        except FileNotFoundError as e:
            error = e
            pass
    if error:
        raise error
