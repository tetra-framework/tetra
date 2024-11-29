from django.shortcuts import render
from django.http import Http404
from django.conf import settings
import yaml
import markdown
from markdown.extensions.toc import TocExtension


def markdown_title(title) -> str:
    return markdown.markdown(title).replace("<p>", "").replace("</p>", "")


def doc(request, slug="introduction"):
    with open(settings.BASE_DIR.parent / "docs" / "structure.yaml") as f:
        raw_structure = yaml.load(f, Loader=yaml.CLoader)
    structure = []
    slugs = []
    for top_level in raw_structure:
        key, value = next(iter(top_level.items()))
        if isinstance(value, str):
            # Header with link
            slugs.append(key)
            structure.append(
                {
                    "slug": key,
                    "title": markdown_title(value),
                    "items": [],
                }
            )
        else:
            # Header with sub items
            items = []
            for item in value:
                item_key, item_value = next(iter(item.items()))
                slugs.append(item_key)
                items.append(
                    {
                        "slug": item_key,
                        "title": markdown_title(item_value),
                    }
                )
            structure.append(
                {
                    "slug": None,
                    "title": markdown_title(key),
                    "items": items,
                }
            )

    if slug not in slugs:
        raise Http404()

    with open(settings.BASE_DIR.parent / "docs" / f"{slug}.md") as f:
        md = markdown.Markdown(
            extensions=[
                "extra",
                "meta",
                TocExtension(permalink="#", toc_depth=3),
            ]
        )
        content = md.convert(f.read())
    print(md.Meta)
    return render(
        request,
        "base_docs.html",
        {
            "structure": structure,
            "content": content,
            "toc": md.toc,
            "active_slug": slug,
            "title": " ".join(md.Meta["title"]),
        },
    )
