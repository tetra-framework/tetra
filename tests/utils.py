from bs4 import BeautifulSoup, Tag


def extract_component(html: str | bytes, innerHTML=True) -> str:
    """Helper to extract the `div#component` content from the given HTML.
    Also cuts out ALL newlines from the output.
    if innerHTML is False, it will return the outerHTML, including the HTML tag and
    attributes. If False, it returns only the inner content.
    """
    el = BeautifulSoup(html, features="html.parser").html.body.find(id="component")
    if innerHTML:
        return el.decode_contents().replace("\n", "")
    else:
        return str(el).replace("\n", "")


def extract_component_tag(html: str | bytes) -> Tag:
    """Helper to extract the `div#component` content from the given HTML as
    BeautifulSoup parsed entity."""
    return BeautifulSoup(html, features="html.parser").html.body.find(id="component")
