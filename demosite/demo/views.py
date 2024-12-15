import logging
import os
import re

import markdown
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from markdown.extensions.toc import TocExtension

from .utils import prepopulate_session_to_do

logger = logging.getLogger(__name__)

FIRST_SLUG = "introduction"


def home(request) -> HttpResponse:
    prepopulate_session_to_do(request)
    return render(request, "index.html")


def titlify(slug: str) -> str:
    return slug.replace("_", " ").title()


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
    # TODO cache this!
    for entry in os.scandir(examples_dir):
        if entry.name == FIRST_SLUG:
            continue
        if entry.is_dir(follow_symlinks=False):
            structure[entry.name] = {"slug": entry.name, "title": titlify(entry.name)}

    if slug not in structure and slug != FIRST_SLUG:
        raise Http404()

    with open(examples_dir / slug / "text.md") as f:
        md = markdown.Markdown(
            extensions=[
                "extra",
                "meta",
                TocExtension(permalink="#", toc_depth=3),
            ]
        )
        content = md.convert(f.read())
        demo_html = ""
        # if there exists a demo, add it
        try:
            demo_html = render_to_string(
                examples_dir / slug / "demo.html", request=request
            )
            if demo_html:
                content += "<hr class='hr'/><h2>Demo</h2>"
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
                "title": " ".join(md.Meta["title"]),
                "has_demo": bool(demo_html),
            },
        )
