from django.http import HttpRequest
from django.template import Template, RequestContext


def render_component_tag(
    request_with_session: HttpRequest, component_string, context=None
):
    """Helper function to return a full html document with loaded Tetra stuff,
    and the component_string as body content.

    Attributes:
        request: The request object.
        component_string: The string to be rendered - usually something like
            '{% MyComponent / %}'.
        context: The context the template is rendered with. This is the outer context
            of the component
    """
    ctx = RequestContext(request_with_session)
    if context:
        ctx.update(context)
    ctx.request = request_with_session
    return Template(
        "{% load tetra %}<!doctype html>"
        "<html><head>"
        "{% tetra_styles %}"
        "{% tetra_scripts include_alpine=True %}"
        "</head><body>"
        f"{component_string}"
        "</body></html>"
    ).render(ctx)
