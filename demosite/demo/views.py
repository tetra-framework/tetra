import logging
import os
import re

import markdown
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.template import TemplateDoesNotExist, Template, RequestContext
from django.template.loader import render_to_string
from django.utils.translation import gettext as _, get_language
from markdown.extensions.toc import TocExtension

from .utils import prepopulate_session_to_do

logger = logging.getLogger(__name__)

FIRST_SLUG = "introduction"


def home(request) -> HttpResponse:
    prepopulate_session_to_do(request)
    # TODO: purge entries from sessions older than 30 days
    return render(request, "index.html")


def titlify(slug: str) -> str:
    return _(slug.replace("_", " ").title())


def markdown_title(title) -> str:
    return markdown.markdown(title).replace("<p>", "").replace("</p>", "")


def examples(request, slug: str = FIRST_SLUG) -> HttpResponse:
    slug = slug.lower()
    if not re.match(r"^[a-zA-Z0-9_]+$", slug):
        raise Http404()

    examples_dir = settings.BASE_DIR / "demo" / "templates" / "examples"
    # keep Sam's "structure", as we may need it later, when more examples need to be
    # structured into sections
    structure = {}
    language_code = get_language()
    md_meta_parser = markdown.Markdown(extensions=["meta"])
    # TODO cache this!
    for entry in os.scandir(examples_dir):
        if entry.name == FIRST_SLUG:
            continue
        if entry.is_dir(follow_symlinks=False):
            example_slug = entry.name
            title = titlify(example_slug)  # Fallback title

            md_file_path = examples_dir / example_slug / f"text.{language_code}.md"
            if not md_file_path.exists():
                md_file_path = examples_dir / example_slug / "text.md"

            if md_file_path.exists():
                with open(md_file_path, encoding="utf-8") as f:
                    md_content = f.read()
                    md_meta_parser.reset()
                    md_meta_parser.convert(md_content)
                    if "title" in md_meta_parser.Meta and md_meta_parser.Meta["title"]:
                        title = " ".join(md_meta_parser.Meta["title"])
            structure[entry.name] = {"slug": entry.name, "title": title}

    if slug not in structure and slug != FIRST_SLUG:
        raise Http404()

    md = markdown.Markdown(
        extensions=[
            "extra",
            "meta",
            TocExtension(permalink="#", toc_depth=3),
        ]
    )
    # first, render the markdown from text.md
    md_file_path = examples_dir / slug / f"text.{language_code}.md"
    if not md_file_path.exists():
        md_file_path = examples_dir / slug / "text.md"

    with open(md_file_path, encoding="utf-8") as f:
        # assume content has Django template directives, render them first
        content = Template("{% load demo_tags %}" + f.read()).render(
            context=RequestContext(request)
        )
        content = md.convert(content)

    # # then render component code, if available
    # try:
    #     component = resolve_component(None, f"demo.examples.{slug}")
    #     if component:
    #         filename, start, length = component.get_source_location()
    #         with open(filename) as f:
    #             # this only works if each component is located in one file
    #             content += md.convert(
    #                 "```python\n" + "# component source code\n" + f.read() + "\n```"
    #             )
    #             # content += """<div class="pt-2 ps-3 border-top border-secondary text-muted small"><b>models.py</b></div>"""
    #         content += md.convert(
    #             "```django\n# file template\n"
    #             + component._read_component_file_with_extension("html")
    #             + "\n```"
    #         )
    # except ComponentNotFound:
    #     pass

    # if there exists a demo, add it
    demo_html = ""
    try:
        demo_html = render_to_string(examples_dir / slug / "demo.html", request=request)
        if demo_html:
            content += f"<hr class='hr'/><h2>{_('Demo')}</h2>"
            content += demo_html
    except TemplateDoesNotExist:
        pass

    logger.debug(md.Meta)
    return render(
        request,
        "base_examples.html",
        {
            "structure": structure,
            "FIRST_SLUG": {"slug": FIRST_SLUG, "title": titlify(FIRST_SLUG)},
            "content": content,
            "toc": md.toc,
            "active_slug": slug,
            "title": " ".join(md.Meta["title"]) if "title" in md.Meta else "",
            "has_demo": bool(demo_html),
        },
    )
